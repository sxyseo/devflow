/**
 * DevFlow Dashboard Backend - Control Route
 *
 * API endpoints for controlling DevFlow system actions.
 */

const express = require('express');
const fs = require('fs').promises;
const path = require('path');

const router = express.Router();

const STATE_FILE = path.join(__dirname, '../../../.devflow/state/system_state.json');
const TASKS_DIR = path.join(__dirname, '../../../.devflow/tasks');

/**
 * POST /api/control/inject-task
 *
 * Inject a new task into the DevFlow system.
 * Request body:
 * - type: Task type (e.g., 'development', 'testing', 'documentation')
 * - description: Task description
 * - priority: Task priority (1-5, default: 3)
 * - metadata: Optional additional metadata
 */
router.post('/inject-task', async (req, res) => {
  try {
    const { type, description, priority = 3, metadata = {} } = req.body;

    // Validate required fields
    if (!type) {
      return res.status(400).json({ error: 'Missing required field: type' });
    }
    if (!description) {
      return res.status(400).json({ error: 'Missing required field: description' });
    }

    // Validate priority range
    const taskPriority = parseInt(priority, 10);
    if (isNaN(taskPriority) || taskPriority < 1 || taskPriority > 5) {
      return res.status(400).json({ error: 'Priority must be between 1 and 5' });
    }

    // Generate task ID with UUID format for consistency
    const taskId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create task object with all required fields
    const task = {
      id: taskId,
      type,
      description,
      priority: taskPriority,
      status: 'pending',
      dependencies: [],
      assigned_to: null,
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: null,
      result: null,
      error: null,
      retry_count: 0,
      metadata
    };

    // Load current system state
    let systemState;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      systemState = JSON.parse(stateData);
    } catch (error) {
      // If state file doesn't exist, create minimal state
      systemState = {
        agents: {},
        tasks: {},
        workflows: {},
        metrics: {}
      };
    }

    // Add task to system state
    if (!systemState.tasks) {
      systemState.tasks = {};
    }
    systemState.tasks[taskId] = task;

    // Write updated system state back to file
    await fs.writeFile(STATE_FILE, JSON.stringify(systemState, null, 2));

    // Ensure tasks directory exists
    try {
      await fs.mkdir(TASKS_DIR, { recursive: true });
    } catch (error) {
      // Directory might already exist, ignore error
    }

    // Write task to individual file (for backup/logging)
    const taskFile = path.join(TASKS_DIR, `${taskId}.json`);
    await fs.writeFile(taskFile, JSON.stringify(task, null, 2));

    // Return created task
    res.status(201).json({
      success: true,
      task,
      message: 'Task injected successfully'
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * POST /api/control/stop-agent
 *
 * Stop a running agent by ID.
 * Request body:
 * - agentId: ID of the agent to stop
 */
router.post('/stop-agent', async (req, res) => {
  try {
    const { agentId } = req.body;

    if (!agentId) {
      return res.status(400).json({ error: 'Missing required field: agentId' });
    }

    // Load current state to verify agent exists
    let state;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      state = JSON.parse(stateData);
    } catch (error) {
      return res.status(500).json({ error: 'Failed to load system state' });
    }

    // Check if agent exists
    if (!state.agents || !state.agents[agentId]) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    // Update agent status to stopped
    state.agents[agentId].status = 'stopped';
    state.agents[agentId].stoppedAt = new Date().toISOString();

    // Write updated state back
    await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2));

    res.json({
      success: true,
      agentId,
      message: 'Agent stopped successfully'
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * POST /api/control/restart-agent
 *
 * Restart a stopped or failed agent by ID.
 * Request body:
 * - agentId: ID of the agent to restart
 */
router.post('/restart-agent', async (req, res) => {
  try {
    const { agentId } = req.body;

    if (!agentId) {
      return res.status(400).json({ error: 'Missing required field: agentId' });
    }

    // Load current state to verify agent exists
    let state;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      state = JSON.parse(stateData);
    } catch (error) {
      return res.status(500).json({ error: 'Failed to load system state' });
    }

    // Check if agent exists
    if (!state.agents || !state.agents[agentId]) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    // Update agent status to idle (ready to start)
    state.agents[agentId].status = 'idle';
    state.agents[agentId].restartedAt = new Date().toISOString();

    // Write updated state back
    await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2));

    res.json({
      success: true,
      agentId,
      message: 'Agent restarted successfully'
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * POST /api/control/pause-workflow
 *
 * Pause a running workflow by ID.
 * Request body:
 * - workflowId: ID of the workflow to pause
 */
router.post('/pause-workflow', async (req, res) => {
  try {
    const { workflowId } = req.body;

    if (!workflowId) {
      return res.status(400).json({ error: 'Missing required field: workflowId' });
    }

    // Load current state to verify workflow exists
    let state;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      state = JSON.parse(stateData);
    } catch (error) {
      return res.status(500).json({ error: 'Failed to load system state' });
    }

    // Check if workflow exists
    if (!state.workflows || !state.workflows[workflowId]) {
      return res.status(404).json({ error: 'Workflow not found' });
    }

    // Update workflow status to paused
    state.workflows[workflowId].status = 'paused';
    state.workflows[workflowId].pausedAt = new Date().toISOString();

    // Write updated state back
    await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2));

    res.json({
      success: true,
      workflowId,
      message: 'Workflow paused successfully'
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * POST /api/control/resume-workflow
 *
 * Resume a paused workflow by ID.
 * Request body:
 * - workflowId: ID of the workflow to resume
 */
router.post('/resume-workflow', async (req, res) => {
  try {
    const { workflowId } = req.body;

    if (!workflowId) {
      return res.status(400).json({ error: 'Missing required field: workflowId' });
    }

    // Load current state to verify workflow exists
    let state;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      state = JSON.parse(stateData);
    } catch (error) {
      return res.status(500).json({ error: 'Failed to load system state' });
    }

    // Check if workflow exists
    if (!state.workflows || !state.workflows[workflowId]) {
      return res.status(404).json({ error: 'Workflow not found' });
    }

    // Update workflow status to running
    state.workflows[workflowId].status = 'running';
    state.workflows[workflowId].resumedAt = new Date().toISOString();

    // Write updated state back
    await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2));

    res.json({
      success: true,
      workflowId,
      message: 'Workflow resumed successfully'
    });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

module.exports = router;
