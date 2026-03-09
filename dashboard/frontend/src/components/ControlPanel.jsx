/**
 * ControlPanel Component
 *
 * Provides manual control capabilities for the DevFlow system including
 * task injection, agent management, and workflow control.
 */

import React, { useState, useEffect } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

function ControlPanel() {
  const [agents, setAgents] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);

  // Task injection form state
  const [taskType, setTaskType] = useState('development');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskPriority, setTaskPriority] = useState(3);
  const [taskMetadata, setTaskMetadata] = useState('');
  const [injectingTask, setInjectingTask] = useState(false);
  const [taskMessage, setTaskMessage] = useState(null);

  // Agent control state
  const [controllingAgent, setControllingAgent] = useState(null);

  // Workflow control state
  const [controllingWorkflow, setControllingWorkflow] = useState(null);

  useEffect(() => {
    fetchAgents();
    fetchWorkflows();
    const interval = setInterval(() => {
      fetchAgents();
      fetchWorkflows();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/agents`);
      const data = await response.json();
      setAgents(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching agents:', error);
      setLoading(false);
    }
  };

  const fetchWorkflows = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/workflows`);
      const data = await response.json();
      setWorkflows(data);
    } catch (error) {
      console.error('Error fetching workflows:', error);
    }
  };

  const handleInjectTask = async (e) => {
    e.preventDefault();
    setInjectingTask(true);
    setTaskMessage(null);

    try {
      const metadata = taskMetadata ? JSON.parse(taskMetadata) : {};
      const response = await fetch(`${API_BASE}/api/control/inject-task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: taskType,
          description: taskDescription,
          priority: taskPriority,
          metadata,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setTaskMessage({
          type: 'success',
          text: `Task injected successfully! ID: ${data.task.id}`,
        });
        // Reset form
        setTaskDescription('');
        setTaskPriority(3);
        setTaskMetadata('');
      } else {
        setTaskMessage({
          type: 'error',
          text: data.error || 'Failed to inject task',
        });
      }
    } catch (error) {
      setTaskMessage({
        type: 'error',
        text: `Error: ${error.message}`,
      });
    } finally {
      setInjectingTask(false);
    }
  };

  const handleStopAgent = async (agentId) => {
    setControllingAgent(agentId);
    try {
      const response = await fetch(`${API_BASE}/api/control/stop-agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ agentId }),
      });

      const data = await response.json();
      if (response.ok) {
        fetchAgents(); // Refresh agent list
      } else {
        console.error('Failed to stop agent:', data.error);
      }
    } catch (error) {
      console.error('Error stopping agent:', error);
    } finally {
      setControllingAgent(null);
    }
  };

  const handleRestartAgent = async (agentId) => {
    setControllingAgent(agentId);
    try {
      const response = await fetch(`${API_BASE}/api/control/restart-agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ agentId }),
      });

      const data = await response.json();
      if (response.ok) {
        fetchAgents(); // Refresh agent list
      } else {
        console.error('Failed to restart agent:', data.error);
      }
    } catch (error) {
      console.error('Error restarting agent:', error);
    } finally {
      setControllingAgent(null);
    }
  };

  const handlePauseWorkflow = async (workflowId) => {
    setControllingWorkflow(workflowId);
    try {
      const response = await fetch(`${API_BASE}/api/control/pause-workflow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ workflowId }),
      });

      const data = await response.json();
      if (response.ok) {
        fetchWorkflows(); // Refresh workflow list
      } else {
        console.error('Failed to pause workflow:', data.error);
      }
    } catch (error) {
      console.error('Error pausing workflow:', error);
    } finally {
      setControllingWorkflow(null);
    }
  };

  const handleResumeWorkflow = async (workflowId) => {
    setControllingWorkflow(workflowId);
    try {
      const response = await fetch(`${API_BASE}/api/control/resume-workflow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ workflowId }),
      });

      const data = await response.json();
      if (response.ok) {
        fetchWorkflows(); // Refresh workflow list
      } else {
        console.error('Failed to resume workflow:', data.error);
      }
    } catch (error) {
      console.error('Error resuming workflow:', error);
    } finally {
      setControllingWorkflow(null);
    }
  };

  if (loading) {
    return (
      <div className="control-panel-loading">
        <div className="spinner"></div>
        <p>Loading control panel...</p>
      </div>
    );
  }

  return (
    <div className="control-panel">
      <div className="control-panel-header">
        <h2>Control Panel</h2>
        <p>Manage tasks, agents, and workflows manually</p>
      </div>

      <div className="control-sections">
        {/* Task Injection Section */}
        <section className="control-section">
          <h3>Inject Task</h3>
          <form onSubmit={handleInjectTask} className="task-injection-form">
            <div className="form-group">
              <label htmlFor="taskType">Task Type</label>
              <select
                id="taskType"
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                disabled={injectingTask}
              >
                <option value="development">Development</option>
                <option value="testing">Testing</option>
                <option value="documentation">Documentation</option>
                <option value="maintenance">Maintenance</option>
                <option value="deployment">Deployment</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="taskDescription">Description</label>
              <textarea
                id="taskDescription"
                value={taskDescription}
                onChange={(e) => setTaskDescription(e.target.value)}
                disabled={injectingTask}
                required
                rows={3}
                placeholder="Describe the task..."
              />
            </div>

            <div className="form-group">
              <label htmlFor="taskPriority">Priority (1-5)</label>
              <input
                id="taskPriority"
                type="number"
                min="1"
                max="5"
                value={taskPriority}
                onChange={(e) => setTaskPriority(parseInt(e.target.value, 10))}
                disabled={injectingTask}
              />
              <small>1 = lowest, 5 = highest</small>
            </div>

            <div className="form-group">
              <label htmlFor="taskMetadata">Metadata (JSON, optional)</label>
              <textarea
                id="taskMetadata"
                value={taskMetadata}
                onChange={(e) => setTaskMetadata(e.target.value)}
                disabled={injectingTask}
                rows={2}
                placeholder='{"key": "value"}'
              />
            </div>

            <button
              type="submit"
              className="btn-primary"
              disabled={injectingTask || !taskDescription}
            >
              {injectingTask ? 'Injecting...' : 'Inject Task'}
            </button>

            {taskMessage && (
              <div className={`message ${taskMessage.type}`}>
                {taskMessage.text}
              </div>
            )}
          </form>
        </section>

        {/* Agent Control Section */}
        <section className="control-section">
          <h3>Agent Control</h3>
          {agents.length === 0 ? (
            <p className="empty-state">No agents available</p>
          ) : (
            <div className="agent-controls-list">
              {agents.map((agent) => (
                <div key={agent.id} className="agent-control-item">
                  <div className="agent-info">
                    <span className="agent-id">{agent.id}</span>
                    <span className={`status ${agent.status}`}>
                      {agent.status}
                    </span>
                  </div>
                  <div className="agent-actions">
                    {agent.status === 'running' && (
                      <button
                        className="btn-danger"
                        onClick={() => handleStopAgent(agent.id)}
                        disabled={controllingAgent === agent.id}
                      >
                        {controllingAgent === agent.id ? 'Stopping...' : 'Stop'}
                      </button>
                    )}
                    {(agent.status === 'stopped' || agent.status === 'failed') && (
                      <button
                        className="btn-success"
                        onClick={() => handleRestartAgent(agent.id)}
                        disabled={controllingAgent === agent.id}
                      >
                        {controllingAgent === agent.id ? 'Restarting...' : 'Restart'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Workflow Control Section */}
        <section className="control-section">
          <h3>Workflow Control</h3>
          {workflows.length === 0 ? (
            <p className="empty-state">No workflows available</p>
          ) : (
            <div className="workflow-controls-list">
              {workflows.map((workflow) => (
                <div key={workflow.id} className="workflow-control-item">
                  <div className="workflow-info">
                    <span className="workflow-id">{workflow.id}</span>
                    <span className={`status ${workflow.status}`}>
                      {workflow.status}
                    </span>
                  </div>
                  <div className="workflow-actions">
                    {workflow.status === 'running' && (
                      <button
                        className="btn-warning"
                        onClick={() => handlePauseWorkflow(workflow.id)}
                        disabled={controllingWorkflow === workflow.id}
                      >
                        {controllingWorkflow === workflow.id ? 'Pausing...' : 'Pause'}
                      </button>
                    )}
                    {workflow.status === 'paused' && (
                      <button
                        className="btn-success"
                        onClick={() => handleResumeWorkflow(workflow.id)}
                        disabled={controllingWorkflow === workflow.id}
                      >
                        {controllingWorkflow === workflow.id ? 'Resuming...' : 'Resume'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default ControlPanel;
