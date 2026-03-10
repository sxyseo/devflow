/**
 * CostMetrics Component
 *
 * Displays cost metrics and usage data with charts and summaries.
 */

import React, { useState, useEffect } from 'react';
import { Line, Bar } from 'react-chartjs-2';
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
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

function CostMetrics() {
  const [costs, setCosts] = useState(null);
  const [summary, setSummary] = useState(null);
  const [agentCosts, setAgentCosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('daily');

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const socket = io(API_BASE);

    socket.on('costs-update', (data) => {
      if (data) {
        setSummary(data);
        setLoading(false);
      }
    });

    // Initial fetch
    fetchCosts();
    fetchSummary();
    fetchAgentCosts();

    // Periodic refresh as fallback
    const interval = setInterval(() => {
      fetchCosts();
      fetchSummary();
      fetchAgentCosts();
    }, 15000);

    return () => {
      socket.disconnect();
      clearInterval(interval);
    };
  }, [timeframe]);

  const fetchCosts = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/costs?timeframe=${timeframe}&limit=30`);
      const data = await response.json();
      setCosts(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching costs:', error);
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/costs/summary`);
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Error fetching cost summary:', error);
    }
  };

  const fetchAgentCosts = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/costs/by-agent`);
      const data = await response.json();
      setAgentCosts(data);
    } catch (error) {
      console.error('Error fetching agent costs:', error);
    }
  };

  const formatCurrency = (value) => {
    return `$${parseFloat(value).toFixed(4)}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const getCostTrendData = () => {
    if (!costs || !costs.data) return null;

    return {
      labels: costs.data.map(d => formatDate(d.period)),
      datasets: [
        {
          label: 'API Costs',
          data: costs.data.map(d => d.apiCosts),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4
        },
        {
          label: 'Agent Costs',
          data: costs.data.map(d => d.agentCosts),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.4
        },
        {
          label: 'Total Costs',
          data: costs.data.map(d => d.totalCosts),
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          fill: true,
          tension: 0.4
        }
      ]
    };
  };

  const getTaskCountData = () => {
    if (!costs || !costs.data) return null;

    return {
      labels: costs.data.map(d => formatDate(d.period)),
      datasets: [
        {
          label: 'Tasks Completed',
          data: costs.data.map(d => d.taskCount),
          backgroundColor: '#8b5cf6',
          borderRadius: 4
        }
      ]
    };
  };

  const getAgentCostData = () => {
    if (agentCosts.length === 0) return null;

    return {
      labels: agentCosts.map(a => a.agentName),
      datasets: [
        {
          label: 'Total Costs',
          data: agentCosts.map(a => a.totalCosts),
          backgroundColor: agentCosts.map(a => {
            switch (a.status) {
              case 'running': return '#10b981';
              case 'idle': return '#f59e0b';
              case 'halted': return '#ef4444';
              default: return '#6b7280';
            }
          }),
          borderRadius: 4
        }
      ]
    };
  };

  if (loading) {
    return (
      <div className="cost-metrics-loading">
        <div className="spinner"></div>
        <p>Loading cost metrics...</p>
      </div>
    );
  }

  return (
    <div className="cost-metrics">
      <div className="cost-metrics-header">
        <h2>Cost Metrics</h2>
        <div className="timeframe-selector">
          <button
            className={timeframe === 'hourly' ? 'active' : ''}
            onClick={() => setTimeframe('hourly')}
          >
            Hourly
          </button>
          <button
            className={timeframe === 'daily' ? 'active' : ''}
            onClick={() => setTimeframe('daily')}
          >
            Daily
          </button>
          <button
            className={timeframe === 'weekly' ? 'active' : ''}
            onClick={() => setTimeframe('weekly')}
          >
            Weekly
          </button>
          <button
            className={timeframe === 'monthly' ? 'active' : ''}
            onClick={() => setTimeframe('monthly')}
          >
            Monthly
          </button>
        </div>
      </div>

      {summary && (
        <div className="cost-summary-cards">
          <div className="cost-card">
            <div className="cost-card-icon">💰</div>
            <div className="cost-card-info">
              <div className="cost-card-title">Total Costs</div>
              <div className="cost-card-value">{formatCurrency(summary.costs.total)}</div>
            </div>
          </div>
          <div className="cost-card">
            <div className="cost-card-icon">🔌</div>
            <div className="cost-card-info">
              <div className="cost-card-title">API Costs</div>
              <div className="cost-card-value">{formatCurrency(summary.costs.api)}</div>
            </div>
          </div>
          <div className="cost-card">
            <div className="cost-card-icon">🤖</div>
            <div className="cost-card-info">
              <div className="cost-card-title">Agent Costs</div>
              <div className="cost-card-value">{formatCurrency(summary.costs.agents)}</div>
            </div>
          </div>
          <div className="cost-card">
            <div className="cost-card-icon">📊</div>
            <div className="cost-card-info">
              <div className="cost-card-title">Avg Cost/Task</div>
              <div className="cost-card-value">{formatCurrency(summary.tasks.averageCostPerTask)}</div>
            </div>
          </div>
        </div>
      )}

      {costs && costs.summary && (
        <div className="cost-summary-stats">
          <div className="stat-item">
            <span className="stat-label">Total Tasks:</span>
            <span className="stat-value">{costs.summary.totalTasks}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Total API Costs:</span>
            <span className="stat-value">{formatCurrency(costs.summary.totalApiCosts)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Total Agent Costs:</span>
            <span className="stat-value">{formatCurrency(costs.summary.totalAgentCosts)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Timeframe:</span>
            <span className="stat-value">{timeframe}</span>
          </div>
        </div>
      )}

      <div className="cost-charts">
        {getCostTrendData() && (
          <div className="chart-container">
            <h3>Cost Trends Over Time</h3>
            <Line data={getCostTrendData()} options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  labels: { color: '#94a3b8' }
                }
              },
              scales: {
                x: {
                  ticks: { color: '#94a3b8' },
                  grid: { color: '#334155' }
                },
                y: {
                  ticks: { color: '#94a3b8' },
                  grid: { color: '#334155' }
                }
              }
            }} />
          </div>
        )}

        {getTaskCountData() && (
          <div className="chart-container">
            <h3>Tasks Completed Over Time</h3>
            <Bar data={getTaskCountData()} options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  labels: { color: '#94a3b8' }
                }
              },
              scales: {
                x: {
                  ticks: { color: '#94a3b8' },
                  grid: { color: '#334155' }
                },
                y: {
                  ticks: { color: '#94a3b8' },
                  grid: { color: '#334155' }
                }
              }
            }} />
          </div>
        )}

        {getAgentCostData() && (
          <div className="chart-container">
            <h3>Costs by Agent</h3>
            <Bar data={getAgentCostData()} options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  labels: { color: '#94a3b8' }
                }
              },
              scales: {
                x: {
                  ticks: { color: '#94a3b8' },
                  grid: { color: '#334155' }
                },
                y: {
                  ticks: { color: '#94a3b8' },
                  grid: { color: '#334155' }
                }
              }
            }} />
          </div>
        )}
      </div>

      {agentCosts.length > 0 && (
        <div className="agent-costs-table">
          <h3>Agent Cost Breakdown</h3>
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Status</th>
                <th>Tasks</th>
                <th>API Costs</th>
                <th>Agent Costs</th>
                <th>Total Costs</th>
              </tr>
            </thead>
            <tbody>
              {agentCosts.map(agent => (
                <tr key={agent.agentId}>
                  <td>{agent.agentName}</td>
                  <td>
                    <span className={`status ${agent.status}`}>
                      {agent.status}
                    </span>
                  </td>
                  <td>{agent.taskCount}</td>
                  <td>{formatCurrency(agent.apiCosts)}</td>
                  <td>{formatCurrency(agent.agentCosts)}</td>
                  <td><strong>{formatCurrency(agent.totalCosts)}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default CostMetrics;
