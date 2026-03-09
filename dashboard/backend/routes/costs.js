/**
 * DevFlow Dashboard Backend - Costs Route
 *
 * API endpoints for retrieving cost metrics and usage data.
 */

const express = require('express');
const fs = require('fs').promises;
const path = require('path');

const router = express.Router();

const STATE_FILE = path.join(__dirname, '../../../.devflow/state/system_state.json');

/**
 * GET /api/costs
 *
 * Retrieve cost metrics for the DevFlow system.
 * Query parameters:
 * - timeframe: Time period for cost aggregation (default: 'daily')
 *   Options: 'hourly', 'daily', 'weekly', 'monthly'
 * - limit: Number of time periods to return (default: 30)
 */
router.get('/', async (req, res) => {
  try {
    const { timeframe = 'daily', limit = 30 } = req.query;
    const periodsLimit = parseInt(limit, 10) || 30;

    // Try to load actual state data
    let costData;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      const state = JSON.parse(stateData);
      costData = calculateCostMetrics(state, timeframe, periodsLimit);
    } catch (error) {
      // If state file is not available, return mock data
      costData = getMockCostData(timeframe, periodsLimit);
    }

    res.json(costData);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * GET /api/costs/summary
 *
 * Retrieve a summary of overall cost metrics.
 */
router.get('/summary', async (req, res) => {
  try {
    let summaryData;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      const state = JSON.parse(stateData);
      summaryData = calculateCostSummary(state);
    } catch (error) {
      // If state file is not available, return mock data
      summaryData = getMockCostSummary();
    }

    res.json(summaryData);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * GET /api/costs/by-agent
 *
 * Retrieve cost breakdown by agent.
 */
router.get('/by-agent', async (req, res) => {
  try {
    let agentCosts;
    try {
      const stateData = await fs.readFile(STATE_FILE, 'utf8');
      const state = JSON.parse(stateData);
      agentCosts = calculateCostsByAgent(state);
    } catch (error) {
      // If state file is not available, return mock data
      agentCosts = getMockCostsByAgent();
    }

    res.json(agentCosts);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * Calculate cost metrics from system state
 */
function calculateCostMetrics(state, timeframe, limit) {
  const tasks = Object.values(state.tasks || {});
  const agents = Object.values(state.agents || {});

  // Group costs by time period
  const costsByPeriod = {};
  const now = new Date();

  for (let i = 0; i < limit; i++) {
    const periodKey = getPeriodKey(now, i, timeframe);
    costsByPeriod[periodKey] = {
      period: periodKey,
      timestamp: getPeriodTimestamp(now, i, timeframe),
      apiCosts: 0,
      agentCosts: 0,
      totalCosts: 0,
      taskCount: 0,
      agentCount: agents.length
    };
  }

  // Aggregate task costs
  for (const task of tasks) {
    if (task.costs) {
      const periodKey = getPeriodKeyFromTimestamp(task.completedAt || task.createdAt, timeframe);
      if (costsByPeriod[periodKey]) {
        costsByPeriod[periodKey].apiCosts += task.costs.api || 0;
        costsByPeriod[periodKey].agentCosts += task.costs.agent || 0;
        costsByPeriod[periodKey].totalCosts += (task.costs.api || 0) + (task.costs.agent || 0);
        costsByPeriod[periodKey].taskCount += 1;
      }
    }
  }

  return {
    timeframe,
    data: Object.values(costsByPeriod).reverse(),
    summary: {
      totalApiCosts: Object.values(costsByPeriod).reduce((sum, p) => sum + p.apiCosts, 0),
      totalAgentCosts: Object.values(costsByPeriod).reduce((sum, p) => sum + p.agentCosts, 0),
      totalCosts: Object.values(costsByPeriod).reduce((sum, p) => sum + p.totalCosts, 0),
      totalTasks: Object.values(costsByPeriod).reduce((sum, p) => sum + p.taskCount, 0)
    }
  };
}

/**
 * Calculate overall cost summary
 */
function calculateCostSummary(state) {
  const tasks = Object.values(state.tasks || {});
  const agents = Object.values(state.agents || {});

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
      api: totalApiCosts,
      agents: totalAgentCosts,
      total: totalApiCosts + totalAgentCosts
    },
    tasks: {
      total: totalTasks,
      completed: completedTasks,
      averageCostPerTask: totalTasks > 0 ? ((totalApiCosts + totalAgentCosts) / totalTasks).toFixed(4) : 0
    },
    agents: {
      total: agents.length,
      active: agents.filter(a => a.status === 'running').length
    }
  };
}

/**
 * Calculate costs broken down by agent
 */
function calculateCostsByAgent(state) {
  const agents = Object.values(state.agents || {});
  const tasks = Object.values(state.tasks || {});

  const agentCosts = {};

  for (const agent of agents) {
    agentCosts[agent.id] = {
      agentId: agent.id,
      agentName: agent.name || agent.id,
      status: agent.status,
      taskCount: 0,
      totalCosts: 0,
      apiCosts: 0,
      agentCosts: 0
    };
  }

  for (const task of tasks) {
    if (task.agentId && agentCosts[task.agentId]) {
      agentCosts[task.agentId].taskCount += 1;
      if (task.costs) {
        agentCosts[task.agentId].apiCosts += task.costs.api || 0;
        agentCosts[task.agentId].agentCosts += task.costs.agent || 0;
        agentCosts[task.agentId].totalCosts += (task.costs.api || 0) + (task.costs.agent || 0);
      }
    }
  }

  return Object.values(agentCosts);
}

/**
 * Get period key for a given date and timeframe
 */
function getPeriodKey(date, offset, timeframe) {
  const d = new Date(date);

  switch (timeframe) {
    case 'hourly':
      d.setHours(d.getHours() - offset);
      return d.toISOString().slice(0, 13) + ':00';
    case 'daily':
      d.setDate(d.getDate() - offset);
      return d.toISOString().slice(0, 10);
    case 'weekly':
      d.setDate(d.getDate() - (offset * 7));
      const weekStart = new Date(d);
      weekStart.setDate(d.getDate() - d.getDay());
      return weekStart.toISOString().slice(0, 10);
    case 'monthly':
      d.setMonth(d.getMonth() - offset);
      return d.toISOString().slice(0, 7);
    default:
      d.setDate(d.getDate() - offset);
      return d.toISOString().slice(0, 10);
  }
}

/**
 * Get period key from a timestamp string
 */
function getPeriodKeyFromTimestamp(timestamp, timeframe) {
  if (!timestamp) return getPeriodKey(new Date(), 0, timeframe);

  const date = new Date(timestamp);

  switch (timeframe) {
    case 'hourly':
      return date.toISOString().slice(0, 13) + ':00';
    case 'daily':
      return date.toISOString().slice(0, 10);
    case 'weekly':
      const weekStart = new Date(date);
      weekStart.setDate(date.getDate() - date.getDay());
      return weekStart.toISOString().slice(0, 10);
    case 'monthly':
      return date.toISOString().slice(0, 7);
    default:
      return date.toISOString().slice(0, 10);
  }
}

/**
 * Get timestamp for a period
 */
function getPeriodTimestamp(date, offset, timeframe) {
  const d = new Date(date);

  switch (timeframe) {
    case 'hourly':
      d.setHours(d.getHours() - offset);
      return d.toISOString();
    case 'daily':
      d.setDate(d.getDate() - offset);
      return d.toISOString();
    case 'weekly':
      d.setDate(d.getDate() - (offset * 7));
      return d.toISOString();
    case 'monthly':
      d.setMonth(d.getMonth() - offset);
      return d.toISOString();
    default:
      d.setDate(d.getDate() - offset);
      return d.toISOString();
  }
}

/**
 * Generate mock cost data for when state file is not available
 */
function getMockCostData(timeframe, limit) {
  const data = [];
  const now = new Date();

  for (let i = 0; i < limit; i++) {
    const periodKey = getPeriodKey(now, i, timeframe);
    const apiCosts = parseFloat((Math.random() * 2 + 0.5).toFixed(4));
    const agentCosts = parseFloat((Math.random() * 0.5 + 0.1).toFixed(4));

    data.push({
      period: periodKey,
      timestamp: getPeriodTimestamp(now, i, timeframe),
      apiCosts,
      agentCosts,
      totalCosts: parseFloat((apiCosts + agentCosts).toFixed(4)),
      taskCount: Math.floor(Math.random() * 20) + 5,
      agentCount: 5
    });
  }

  return {
    timeframe,
    data: data.reverse(),
    summary: {
      totalApiCosts: data.reduce((sum, d) => sum + d.apiCosts, 0).toFixed(4),
      totalAgentCosts: data.reduce((sum, d) => sum + d.agentCosts, 0).toFixed(4),
      totalCosts: data.reduce((sum, d) => sum + d.totalCosts, 0).toFixed(4),
      totalTasks: data.reduce((sum, d) => sum + d.taskCount, 0)
    }
  };
}

/**
 * Generate mock cost summary
 */
function getMockCostSummary() {
  return {
    timestamp: new Date().toISOString(),
    costs: {
      api: 45.6789,
      agents: 12.3456,
      total: 58.0245
    },
    tasks: {
      total: 156,
      completed: 142,
      averageCostPerTask: 0.3720
    },
    agents: {
      total: 5,
      active: 3
    }
  };
}

/**
 * Generate mock costs by agent
 */
function getMockCostsByAgent() {
  return [
    {
      agentId: 'agent-1',
      agentName: 'Code Generation Agent',
      status: 'running',
      taskCount: 45,
      totalCosts: 25.4567,
      apiCosts: 20.1234,
      agentCosts: 5.3333
    },
    {
      agentId: 'agent-2',
      agentName: 'Testing Agent',
      status: 'idle',
      taskCount: 32,
      totalCosts: 12.7890,
      apiCosts: 10.2345,
      agentCosts: 2.5545
    },
    {
      agentId: 'agent-3',
      agentName: 'Documentation Agent',
      status: 'running',
      taskCount: 28,
      totalCosts: 8.9123,
      apiCosts: 7.5432,
      agentCosts: 1.3691
    },
    {
      agentId: 'agent-4',
      agentName: 'Review Agent',
      status: 'idle',
      taskCount: 31,
      totalCosts: 6.5432,
      apiCosts: 5.4321,
      agentCosts: 1.1111
    },
    {
      agentId: 'agent-5',
      agentName: 'Deployment Agent',
      status: 'running',
      taskCount: 20,
      totalCosts: 4.3233,
      apiCosts: 2.3457,
      agentCosts: 1.9776
    }
  ];
}

module.exports = router;
