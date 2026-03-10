/**
 * TaskQueue Visualization Component
 *
 * Displays tasks in queue format with dependency graph visualization.
 */

import React, { useState, useEffect } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

function TaskQueue() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState(null);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tasks`);
      const data = await response.json();
      setTasks(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      setLoading(false);
    }
  };

  const getTaskById = (id) => {
    return tasks.find(task => task.id === id);
  };

  const renderDependencyGraph = () => {
    if (tasks.length === 0) {
      return <p className="empty-state">No tasks in queue</p>;
    }

    const groupedTasks = {
      pending: tasks.filter(t => t.status === 'pending'),
      in_progress: tasks.filter(t => t.status === 'in_progress'),
      completed: tasks.filter(t => t.status === 'completed'),
      failed: tasks.filter(t => t.status === 'failed')
    };

    return (
      <div className="dependency-graph">
        {Object.entries(groupedTasks).map(([status, statusTasks]) => (
          statusTasks.length > 0 && (
            <div key={status} className={`task-column ${status}`}>
              <h3 className="column-title">
                {status.replace('_', ' ').toUpperCase()}
                <span className="task-count">{statusTasks.length}</span>
              </h3>
              <div className="task-nodes">
                {statusTasks.map(task => (
                  <div
                    key={task.id}
                    className={`task-node ${selectedTask?.id === task.id ? 'selected' : ''}`}
                    onClick={() => setSelectedTask(task)}
                  >
                    <div className="task-header">
                      <span className="task-type">{task.type}</span>
                      <span className="task-priority">{task.priority}</span>
                    </div>
                    <div className="task-description">
                      {task.description?.substring(0, 80)}
                      {task.description?.length > 80 ? '...' : ''}
                    </div>
                    {task.dependencies && task.dependencies.length > 0 && (
                      <div className="task-dependencies">
                        <span className="dependencies-label">Dependencies:</span>
                        {task.dependencies.map(depId => {
                          const depTask = getTaskById(depId);
                          return depTask ? (
                            <span key={depId} className={`dependency-badge ${depTask.status}`}>
                              {depTask.type}
                            </span>
                          ) : null;
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        ))}
      </div>
    );
  };

  const renderTaskDetails = () => {
    if (!selectedTask) {
      return (
        <div className="task-details-empty">
          <p>Select a task to view details</p>
        </div>
      );
    }

    return (
      <div className="task-details">
        <h3>Task Details</h3>
        <div className="detail-row">
          <span className="detail-label">ID:</span>
          <span className="detail-value">{selectedTask.id}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Type:</span>
          <span className="detail-value">{selectedTask.type}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Status:</span>
          <span className={`detail-value status ${selectedTask.status}`}>
            {selectedTask.status}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Priority:</span>
          <span className="detail-value">{selectedTask.priority}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Description:</span>
          <span className="detail-value">{selectedTask.description}</span>
        </div>
        {selectedTask.dependencies && selectedTask.dependencies.length > 0 && (
          <div className="detail-row">
            <span className="detail-label">Dependencies:</span>
            <div className="detail-value">
              {selectedTask.dependencies.map(depId => {
                const depTask = getTaskById(depId);
                return depTask ? (
                  <div key={depId} className={`dependency-item ${depTask.status}`}>
                    {depTask.type} ({depTask.status})
                  </div>
                ) : (
                  <div key={depId} className="dependency-item unknown">
                    Unknown task: {depId}
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {selectedTask.created_at && (
          <div className="detail-row">
            <span className="detail-label">Created:</span>
            <span className="detail-value">
              {new Date(selectedTask.created_at).toLocaleString()}
            </span>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="task-queue-loading">
        <div className="spinner"></div>
        <p>Loading task queue...</p>
      </div>
    );
  }

  return (
    <div className="task-queue">
      <div className="task-queue-header">
        <h2>Task Queue Visualization</h2>
        <div className="queue-stats">
          <span className="stat">
            Total: <strong>{tasks.length}</strong>
          </span>
          <span className="stat pending">
            Pending: <strong>{tasks.filter(t => t.status === 'pending').length}</strong>
          </span>
          <span className="stat in-progress">
            In Progress: <strong>{tasks.filter(t => t.status === 'in_progress').length}</strong>
          </span>
          <span className="stat completed">
            Completed: <strong>{tasks.filter(t => t.status === 'completed').length}</strong>
          </span>
        </div>
      </div>

      <div className="task-queue-content">
        <div className="graph-container">
          {renderDependencyGraph()}
        </div>
        <div className="details-panel">
          {renderTaskDetails()}
        </div>
      </div>
    </div>
  );
}

export default TaskQueue;
