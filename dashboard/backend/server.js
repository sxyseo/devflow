/**
 * DevFlow Dashboard Backend
 *
 * Express server providing API endpoints for monitoring DevFlow system.
 */

const express = require('express');
const cors = require('cors');
const { Server } = require('socket.io');
const http = require('http');
const fs = require('fs').promises;
const path = require('path');

// Import routes
const commitsRouter = require('./routes/commits');
const costsRouter = require('./routes/costs');
const controlRouter = require('./routes/control');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 3001;
const STATE_FILE = path.join(__dirname, '../../.devflow/state/system_state.json');

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend/dist')));

// State management
let systemState = {
  agents: {},
  tasks: {},
  workflows: {},
  metrics: {}
};

// Load state periodically
async function loadState() {
  try {
    const data = await fs.readFile(STATE_FILE, 'utf8');
    systemState = JSON.parse(data);
  } catch (error) {
    console.error('Error loading state:', error.message);
  }
}

// Load state initially and every 5 seconds
loadState();
setInterval(loadState, 5000);

// API Routes

// Mount routers
app.use('/api/commits', commitsRouter);
app.use('/api/costs', costsRouter);
app.use('/api/control', controlRouter);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// System status
app.get('/api/status', (req, res) => {
  const metrics = calculateMetrics();
  res.json(metrics);
});

// Agents
app.get('/api/agents', (req, res) => {
  const agents = Object.values(systemState.agents || {});
  res.json(agents);
});

app.get('/api/agents/:id', (req, res) => {
  const agent = systemState.agents[req.params.id];
  if (!agent) {
    return res.status(404).json({ error: 'Agent not found' });
  }
  res.json(agent);
});

// Tasks
app.get('/api/tasks', (req, res) => {
  const tasks = Object.values(systemState.tasks || {});

  // Filter by status if provided
  const { status } = req.query;
  if (status) {
    return res.json(tasks.filter(t => t.status === status));
  }

  res.json(tasks);
});

app.get('/api/tasks/:id', (req, res) => {
  const task = systemState.tasks[req.params.id];
  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }
  res.json(task);
});

// Workflows
app.get('/api/workflows', (req, res) => {
  const workflows = Object.values(systemState.workflows || {});
  res.json(workflows);
});

// Metrics
app.get('/api/metrics', (req, res) => {
  const metrics = calculateMetrics();
  res.json(metrics);
});

// Logs
app.get('/api/logs', async (req, res) => {
  try {
    const logsDir = path.join(__dirname, '../../.devflow/logs');
    const { limit = 100 } = req.query;

    const files = await fs.readdir(logsDir);
    const logFiles = files.filter(f => f.endsWith('.log')).slice(-limit);

    const logs = [];
    for (const file of logFiles) {
      const content = await fs.readFile(path.join(logsDir, file), 'utf8');
      logs.push({
        file,
        content: content.split('\n').slice(-100) // Last 100 lines
      });
    }

    res.json(logs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Sessions
app.get('/api/sessions', (req, res) => {
  // This would interface with the tmux session manager
  res.json({
    active: [],
    total: 0
  });
});

// Actions
app.post('/api/actions/stop', (req, res) => {
  // Send signal to stop orchestrator
  io.emit('action', { type: 'stop' });
  res.json({ success: true, message: 'Stop signal sent' });
});

app.post('/api/actions/restart', (req, res) => {
  // Send signal to restart
  io.emit('action', { type: 'restart' });
  res.json({ success: true, message: 'Restart signal sent' });
});

// WebSocket connection
io.on('connection', async (socket) => {
  console.log('Client connected:', socket.id);

  // Send current state on connection
  socket.emit('state-update', calculateMetrics());

  // Send initial commits data
  try {
    const initialCommits = await getRecentCommits();
    socket.emit('commits-update', initialCommits);
  } catch (error) {
    console.error('Error sending initial commits:', error.message);
  }

  // Send initial costs data
  try {
    const initialCosts = await getCostSummary();
    socket.emit('costs-update', initialCosts);
  } catch (error) {
    console.error('Error sending initial costs:', error.message);
  }

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Broadcast state updates
setInterval(() => {
  const metrics = calculateMetrics();
  io.emit('state-update', metrics);
}, 5000);

// Broadcast commits updates
setInterval(async () => {
  try {
    const commits = await getRecentCommits();
    io.emit('commits-update', commits);
  } catch (error) {
    console.error('Error broadcasting commits update:', error.message);
  }
}, 10000); // Check for new commits every 10 seconds

// Broadcast costs updates
setInterval(async () => {
  try {
    const costs = await getCostSummary();
    io.emit('costs-update', costs);
  } catch (error) {
    console.error('Error broadcasting costs update:', error.message);
  }
}, 15000); // Update costs every 15 seconds

// Helper functions
function calculateMetrics() {
  const agents = Object.values(systemState.agents || {});
  const tasks = Object.values(systemState.tasks || {});

  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;
  const failedTasks = tasks.filter(t => t.status === 'failed').length;
  const pendingTasks = tasks.filter(t => t.status === 'pending').length;
  const inProgressTasks = tasks.filter(t => t.status === 'in_progress').length;

  const totalAgents = agents.length;
  const idleAgents = agents.filter(a => a.status === 'idle').length;
  const runningAgents = agents.filter(a => a.status === 'running').length;

  return {
    timestamp: new Date().toISOString(),
    tasks: {
      total: totalTasks,
      completed: completedTasks,
      failed: failedTasks,
      pending: pendingTasks,
      inProgress: inProgressTasks,
      successRate: totalTasks > 0 ? (completedTasks / totalTasks * 100).toFixed(1) : 0
    },
    agents: {
      total: totalAgents,
      idle: idleAgents,
      running: runningAgents,
      utilization: totalAgents > 0 ? ((runningAgents / totalAgents) * 100).toFixed(1) : 0
    },
    system: {
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      nodeVersion: process.version
    }
  };
}

/**
 * Get recent commits for WebSocket broadcast
 */
async function getRecentCommits() {
  try {
    const { exec } = require('child_process');
    const repoRoot = path.join(__dirname, '../../../');
    const commitsLimit = 10;

    return new Promise((resolve) => {
      const gitCommand = `cd "${repoRoot}" && git log -${commitsLimit} --pretty=format:'%H|%an|%ae|%ad|%s|%b' --date=iso`;

      exec(gitCommand, { maxBuffer: 1024 * 1024 * 10 }, (error, stdout) => {
        if (error) {
          // Return mock data if git is not available
          resolve(getMockCommitsData(commitsLimit));
          return;
        }

        const commits = parseCommitsData(stdout);
        resolve(commits);
      });
    });
  } catch (error) {
    console.error('Error getting recent commits:', error.message);
    return getMockCommitsData(10);
  }
}

/**
 * Parse git log output for commits
 */
function parseCommitsData(gitOutput) {
  if (!gitOutput || gitOutput.trim() === '') {
    return [];
  }

  const lines = gitOutput.trim().split('\n');
  return lines.map(line => {
    const [hash, author, email, date, subject, ...bodyParts] = line.split('|');
    const body = bodyParts.join('|') || '';

    return {
      hash,
      shortHash: hash.substring(0, 7),
      author: {
        name: author,
        email: email
      },
      date: date,
      message: {
        subject: subject || '',
        body: body || ''
      }
    };
  });
}

/**
 * Get mock commits data for when git is not available
 */
function getMockCommitsData(limit) {
  const mockCommits = [
    {
      hash: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
      shortHash: 'a1b2c3d',
      author: {
        name: 'Auto Claude',
        email: 'auto-claude@devflow.local'
      },
      date: new Date().toISOString(),
      message: {
        subject: 'feat: Add real-time WebSocket events',
        body: 'Implement commits-update and costs-update events'
      }
    },
    {
      hash: 'b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1',
      shortHash: 'b2c3d4e',
      author: {
        name: 'Auto Claude',
        email: 'auto-claude@devflow.local'
      },
      date: new Date(Date.now() - 3600000).toISOString(),
      message: {
        subject: 'fix: Improve error handling in API routes',
        body: 'Add better error messages and logging'
      }
    }
  ];

  return mockCommits.slice(0, limit);
}

/**
 * Get cost summary for WebSocket broadcast
 */
async function getCostSummary() {
  try {
    const tasks = Object.values(systemState.tasks || {});
    const agents = Object.values(systemState.agents || {});

    let totalApiCosts = 0;
    let totalAgentCosts = 0;
    let totalTasks = tasks.length;
    let completedTasks = 0;

    for (const task of tasks) {
      if (task.costs) {
        totalApiCosts += task.costs.api || 0;
        totalAgentCosts += task.costs.agent || 0;
      }
      if (task.status === 'completed') {
        completedTasks += 1;
      }
    }

    return {
      timestamp: new Date().toISOString(),
      costs: {
        api: parseFloat(totalApiCosts.toFixed(4)),
        agents: parseFloat(totalAgentCosts.toFixed(4)),
        total: parseFloat((totalApiCosts + totalAgentCosts).toFixed(4))
      },
      tasks: {
        total: totalTasks,
        completed: completedTasks,
        averageCostPerTask: totalTasks > 0 ? parseFloat(((totalApiCosts + totalAgentCosts) / totalTasks).toFixed(4)) : 0
      },
      agents: {
        total: agents.length,
        active: agents.filter(a => a.status === 'running').length
      }
    };
  } catch (error) {
    console.error('Error getting cost summary:', error.message);
    return {
      timestamp: new Date().toISOString(),
      costs: {
        api: 0,
        agents: 0,
        total: 0
      },
      tasks: {
        total: 0,
        completed: 0,
        averageCostPerTask: 0
      },
      agents: {
        total: 0,
        active: 0
      }
    };
  }
}

// Serve frontend for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/dist/index.html'));
});

// Start server
server.listen(PORT, () => {
  console.log(`DevFlow Dashboard backend running on port ${PORT}`);
  console.log(`API available at http://localhost:${PORT}/api`);
  console.log(`Dashboard available at http://localhost:${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
