/**
 * DevFlow Dashboard API Utilities
 *
 * Centralized API client for communicating with DevFlow backend.
 * All API calls should use these utilities for consistency.
 */

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

/**
 * Generic fetch wrapper with error handling
 * @param {string} endpoint - API endpoint path
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<object>} Parsed JSON response
 * @throws {Error} Throws error if request fails or returns non-OK status
 */
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Metrics API
 */

/**
 * Fetch current system metrics
 * @returns {Promise<object>} System metrics including tasks, agents, and performance data
 */
export async function fetchMetrics() {
  return fetchAPI('/api/metrics');
}

/**
 * Agents API
 */

/**
 * Fetch all agents
 * @returns {Promise<Array>} List of all agents with their status and statistics
 */
export async function fetchAgents() {
  return fetchAPI('/api/agents');
}

/**
 * Tasks API
 */

/**
 * Fetch all tasks
 * @returns {Promise<Array>} List of all tasks with their status and metadata
 */
export async function fetchTasks() {
  return fetchAPI('/api/tasks');
}

/**
 * Commits API
 */

/**
 * Fetch git commit history
 * @param {number} limit - Maximum number of commits to return (optional)
 * @returns {Promise<Array>} List of recent commits with metadata
 */
export async function fetchCommits(limit = 50) {
  return fetchAPI(`/api/commits?limit=${limit}`);
}

/**
 * Cost Metrics API
 */

/**
 * Fetch cost metrics
 * @param {number} hours - Number of hours to look back for cost data (optional)
 * @returns {Promise<object>} Cost metrics including total, by model, and trends
 */
export async function fetchCosts(hours = 24) {
  return fetchAPI(`/api/costs?hours=${hours}`);
}

/**
 * Control API
 */

/**
 * Inject a new task into the system
 * @param {object} taskData - Task details
 * @param {string} taskData.type - Task type (e.g., 'development', 'testing')
 * @param {string} taskData.description - Task description
 * @param {number} taskData.priority - Task priority (1-5)
 * @returns {Promise<object>} Created task with assigned ID
 */
export async function injectTask(taskData) {
  return fetchAPI('/api/control/inject-task', {
    method: 'POST',
    body: JSON.stringify(taskData),
  });
}

/**
 * Pause the DevFlow system
 * @returns {Promise<object>} System status confirmation
 */
export async function pauseSystem() {
  return fetchAPI('/api/control/pause', {
    method: 'POST',
  });
}

/**
 * Resume the DevFlow system
 * @returns {Promise<object>} System status confirmation
 */
export async function resumeSystem() {
  return fetchAPI('/api/control/resume', {
    method: 'POST',
  });
}

/**
 * WebSocket connection helper
 * Note: Import socket.io-client in your component and pass it as a parameter
 * @param {object} io - Socket.IO client instance
 * @param {object} eventHandlers - Map of event names to handler functions
 * @returns {object} Socket.IO socket instance
 */
export function connectWebSocket(io, eventHandlers = {}) {
  const socket = io(API_BASE);

  // Attach event handlers
  Object.entries(eventHandlers).forEach(([event, handler]) => {
    socket.on(event, handler);
  });

  return socket;
}

/**
 * Export API base URL for reference
 */
export { API_BASE };
