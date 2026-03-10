/**
 * AgentHistory Component
 *
 * Displays agent activity history with timeline visualization.
 */

import React, { useState, useEffect } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

function AgentHistory() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 5000);
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

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const calculateUptime = (agent) => {
    if (!agent.created_at) return 'Unknown';
    const created = new Date(agent.created_at);
    const now = new Date();
    const diff = Math.floor((now - created) / 1000);

    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  };

  const getFilteredAgents = () => {
    if (filter === 'all') return agents;
    return agents.filter(agent => agent.status === filter);
  };

  const renderTimeline = () => {
    const filteredAgents = getFilteredAgents();

    if (filteredAgents.length === 0) {
      return (
        <div className="empty-state">
          <p>No agent history available</p>
        </div>
      );
    }

    // Sort agents by last activity
    const sortedAgents = [...filteredAgents].sort((a, b) => {
      const timeA = new Date(a.updated_at || 0);
      const timeB = new Date(b.updated_at || 0);
      return timeB - timeA;
    });

    return (
      <div className="timeline">
        {sortedAgents.map((agent, index) => (
          <div
            key={agent.id}
            className={`timeline-item ${agent.status} ${selectedAgent?.id === agent.id ? 'selected' : ''}`}
            onClick={() => setSelectedAgent(agent)}
          >
            <div className="timeline-marker">
              <div className={`marker-dot ${agent.status}`}></div>
              {index < sortedAgents.length - 1 && <div className="timeline-line"></div>}
            </div>
            <div className="timeline-content">
              <div className="timeline-header">
                <h3 className="agent-name">{agent.id}</h3>
                <span className={`status ${agent.status}`}>
                  {agent.status}
                </span>
              </div>
              <div className="timeline-meta">
                <span className="agent-type">{agent.type}</span>
                <span className="agent-uptime">Uptime: {calculateUptime(agent)}</span>
              </div>
              <div className="timeline-stats">
                <div className="stat">
                  <span className="stat-label">Completed</span>
                  <span className="stat-value">{agent.tasks_completed || 0}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Failed</span>
                  <span className="stat-value">{agent.tasks_failed || 0}</span>
                </div>
              </div>
              <div className="timeline-time">
                Last active: {formatTimestamp(agent.updated_at)}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderAgentDetails = () => {
    if (!selectedAgent) {
      return (
        <div className="agent-details-empty">
          <p>Select an agent to view details</p>
        </div>
      );
    }

    return (
      <div className="agent-details">
        <h3>Agent Details</h3>
        <div className="detail-row">
          <span className="detail-label">ID:</span>
          <span className="detail-value">{selectedAgent.id}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Type:</span>
          <span className="detail-value">{selectedAgent.type}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Status:</span>
          <span className="detail-value">
            <span className={`status ${selectedAgent.status}`}>
              {selectedAgent.status}
            </span>
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Created:</span>
          <span className="detail-value">{formatTimestamp(selectedAgent.created_at)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Last Updated:</span>
          <span className="detail-value">{formatTimestamp(selectedAgent.updated_at)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Uptime:</span>
          <span className="detail-value">{calculateUptime(selectedAgent)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Tasks Completed:</span>
          <span className="detail-value">{selectedAgent.tasks_completed || 0}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Tasks Failed:</span>
          <span className="detail-value">{selectedAgent.tasks_failed || 0}</span>
        </div>
        {selectedAgent.current_task && (
          <>
            <div className="detail-row">
              <span className="detail-label">Current Task:</span>
              <span className="detail-value">{selectedAgent.current_task}</span>
            </div>
          </>
        )}
        {selectedAgent.error_message && (
          <div className="detail-row">
            <span className="detail-label">Error:</span>
            <span className="detail-value error">{selectedAgent.error_message}</span>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="agent-history-loading">
        <div className="spinner"></div>
        <p>Loading agent history...</p>
      </div>
    );
  }

  return (
    <div className="agent-history">
      <div className="agent-history-header">
        <h2>Agent History</h2>
        <div className="filter-controls">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === 'running' ? 'active' : ''}
            onClick={() => setFilter('running')}
          >
            Running
          </button>
          <button
            className={filter === 'idle' ? 'active' : ''}
            onClick={() => setFilter('idle')}
          >
            Idle
          </button>
          <button
            className={filter === 'halted' ? 'active' : ''}
            onClick={() => setFilter('halted')}
          >
            Halted
          </button>
        </div>
      </div>

      <div className="agent-history-content">
        <div className="timeline-container">
          {renderTimeline()}
        </div>
        <div className="details-panel">
          {renderAgentDetails()}
        </div>
      </div>
    </div>
  );
}

export default AgentHistory;
