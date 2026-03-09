/**
 * DevFlow Dashboard Frontend
 *
 * React application for monitoring DevFlow system.
 */

import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import TaskQueue from './components/TaskQueue';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

function App() {
  const [metrics, setMetrics] = useState(null);
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [connected, setConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    // Connect to WebSocket
    const socket = io(API_BASE);

    socket.on('connect', () => {
      setConnected(true);
      console.log('Connected to server');
    });

    socket.on('disconnect', () => {
      setConnected(false);
      console.log('Disconnected from server');
    });

    socket.on('state-update', (data) => {
      setMetrics(data);
    });

    // Initial data fetch
    fetchMetrics();
    fetchAgents();
    fetchTasks();

    // Periodic refresh
    const interval = setInterval(() => {
      fetchMetrics();
      fetchAgents();
      fetchTasks();
    }, 5000);

    return () => {
      socket.disconnect();
      clearInterval(interval);
    };
  }, []);

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/metrics`);
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error('Error fetching metrics:', error);
    }
  };

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/agents`);
      const data = await response.json();
      setAgents(data);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tasks`);
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  if (!metrics) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading DevFlow Dashboard...</p>
      </div>
    );
  }

  const taskData = {
    labels: ['Completed', 'Failed', 'Pending', 'In Progress'],
    datasets: [{
      data: [
        metrics.tasks.completed,
        metrics.tasks.failed,
        metrics.tasks.pending,
        metrics.tasks.inProgress
      ],
      backgroundColor: [
        '#10b981',
        '#ef4444',
        '#f59e0b',
        '#3b82f6'
      ]
    }]
  };

  const agentData = {
    labels: ['Idle', 'Running'],
    datasets: [{
      data: [metrics.agents.idle, metrics.agents.running],
      backgroundColor: ['#f59e0b', '#10b981']
    }]
  };

  return (
    <div className="dashboard">
      <header>
        <h1>🚀 DevFlow Dashboard</h1>
        <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Connected' : '○ Disconnected'}
        </div>
      </header>

      <nav className="tabs">
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={activeTab === 'agents' ? 'active' : ''}
          onClick={() => setActiveTab('agents')}
        >
          Agents
        </button>
        <button
          className={activeTab === 'tasks' ? 'active' : ''}
          onClick={() => setActiveTab('tasks')}
        >
          Tasks
        </button>
        <button
          className={activeTab === 'queue' ? 'active' : ''}
          onClick={() => setActiveTab('queue')}
        >
          Task Queue
        </button>
      </nav>

      <main>
        {activeTab === 'overview' && (
          <div className="overview">
            <div className="metrics-grid">
              <MetricCard
                title="Total Tasks"
                value={metrics.tasks.total}
                icon="📝"
              />
              <MetricCard
                title="Success Rate"
                value={`${metrics.tasks.successRate}%`}
                icon="✓"
              />
              <MetricCard
                title="Active Agents"
                value={metrics.agents.running}
                icon="🤖"
              />
              <MetricCard
                title="Utilization"
                value={`${metrics.agents.utilization}%`}
                icon="📊"
              />
            </div>

            <div className="charts-grid">
              <div className="chart-card">
                <h3>Tasks</h3>
                <Doughnut data={taskData} />
              </div>
              <div className="chart-card">
                <h3>Agents</h3>
                <Doughnut data={agentData} />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="agents-list">
            <h2>Agents</h2>
            {agents.length === 0 ? (
              <p>No agents found</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Tasks Completed</th>
                    <th>Tasks Failed</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map(agent => (
                    <tr key={agent.id}>
                      <td>{agent.id}</td>
                      <td>{agent.type}</td>
                      <td>
                        <span className={`status ${agent.status}`}>
                          {agent.status}
                        </span>
                      </td>
                      <td>{agent.tasks_completed || 0}</td>
                      <td>{agent.tasks_failed || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'tasks' && (
          <div className="tasks-list">
            <h2>Tasks</h2>
            {tasks.length === 0 ? (
              <p>No tasks found</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map(task => (
                    <tr key={task.id}>
                      <td>{task.type}</td>
                      <td>{task.description?.substring(0, 50)}...</td>
                      <td>
                        <span className={`status ${task.status}`}>
                          {task.status}
                        </span>
                      </td>
                      <td>{task.priority}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'queue' && (
          <TaskQueue />
        )}
      </main>
    </div>
  );
}

function MetricCard({ title, value, icon }) {
  return (
    <div className="metric-card">
      <div className="icon">{icon}</div>
      <div className="info">
        <div className="title">{title}</div>
        <div className="value">{value}</div>
      </div>
    </div>
  );
}

export default App;
