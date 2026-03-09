/**
 * CommitHistory Component
 *
 * Displays git commit history with timeline visualization.
 */

import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3001';

function CommitHistory() {
  const [commits, setCommits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [branch, setBranch] = useState('main');

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const socket = io(API_BASE);

    socket.on('commits-update', (data) => {
      setCommits(data);
      setLoading(false);
    });

    // Initial fetch
    fetchCommits();

    // Periodic refresh
    const interval = setInterval(fetchCommits, 10000);

    return () => {
      socket.disconnect();
      clearInterval(interval);
    };
  }, []);

  const fetchCommits = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/commits?limit=20`);
      const data = await response.json();
      setCommits(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching commits:', error);
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return date.toLocaleDateString();
  };

  const formatFullTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getCommitType = (message) => {
    if (!message || !message.subject) return 'other';

    const subject = message.subject.toLowerCase();

    if (subject.startsWith('feat') || subject.startsWith('feature')) return 'feature';
    if (subject.startsWith('fix') || subject.startsWith('bugfix')) return 'fix';
    if (subject.startsWith('refactor') || subject.startsWith('refactor')) return 'refactor';
    if (subject.startsWith('test') || subject.startsWith('tests')) return 'test';
    if (subject.startsWith('doc') || subject.startsWith('docs')) return 'docs';
    if (subject.startsWith('chore') || subject.startsWith('style')) return 'chore';
    if (subject.startsWith('perf') || subject.startsWith('performance')) return 'performance';

    return 'other';
  };

  const getCommitTypeColor = (type) => {
    switch (type) {
      case 'feature': return '#10b981';
      case 'fix': return '#ef4444';
      case 'refactor': return '#f59e0b';
      case 'test': return '#8b5cf6';
      case 'docs': return '#3b82f6';
      case 'chore': return '#6b7280';
      case 'performance': return '#ec4899';
      default: return '#6b7280';
    }
  };

  const renderTimeline = () => {
    if (commits.length === 0) {
      return (
        <div className="empty-state">
          <p>No commit history available</p>
        </div>
      );
    }

    return (
      <div className="timeline">
        {commits.map((commit, index) => {
          const commitType = getCommitType(commit.message);
          const typeColor = getCommitTypeColor(commitType);

          return (
            <div
              key={commit.hash}
              className={`timeline-item commit-${commitType} ${selectedCommit?.hash === commit.hash ? 'selected' : ''}`}
              onClick={() => setSelectedCommit(commit)}
            >
              <div className="timeline-marker">
                <div
                  className="marker-dot"
                  style={{ backgroundColor: typeColor }}
                ></div>
                {index < commits.length - 1 && <div className="timeline-line"></div>}
              </div>
              <div className="timeline-content">
                <div className="timeline-header">
                  <h3 className="commit-subject">{commit.message.subject}</h3>
                  <span className="commit-hash">{commit.shortHash}</span>
                </div>
                <div className="timeline-meta">
                  <span className="commit-type" style={{ color: typeColor }}>
                    {commitType}
                  </span>
                  <span className="commit-author">{commit.author.name}</span>
                  <span className="commit-time">{formatTimestamp(commit.date)}</span>
                </div>
                {commit.stats && (
                  <div className="commit-stats">
                    <div className="stat">
                      <span className="stat-label">Files</span>
                      <span className="stat-value">{commit.stats.files.length}</span>
                    </div>
                    <div className="stat additions">
                      <span className="stat-label">+</span>
                      <span className="stat-value">{commit.stats.total.additions}</span>
                    </div>
                    <div className="stat deletions">
                      <span className="stat-label">-</span>
                      <span className="stat-value">{commit.stats.total.deletions}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderCommitDetails = () => {
    if (!selectedCommit) {
      return (
        <div className="commit-details-empty">
          <p>Select a commit to view details</p>
        </div>
      );
    }

    const commitType = getCommitType(selectedCommit.message);

    return (
      <div className="commit-details">
        <h3>Commit Details</h3>
        <div className="detail-row">
          <span className="detail-label">Hash:</span>
          <span className="detail-value">{selectedCommit.hash}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Short Hash:</span>
          <span className="detail-value">{selectedCommit.shortHash}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Author:</span>
          <span className="detail-value">{selectedCommit.author.name}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Email:</span>
          <span className="detail-value">{selectedCommit.author.email}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Date:</span>
          <span className="detail-value">{formatFullTimestamp(selectedCommit.date)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Type:</span>
          <span className="detail-value" style={{ color: getCommitTypeColor(commitType) }}>
            {commitType}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Subject:</span>
          <span className="detail-value">{selectedCommit.message.subject}</span>
        </div>
        {selectedCommit.message.body && (
          <div className="detail-row">
            <span className="detail-label">Body:</span>
            <span className="detail-value">{selectedCommit.message.body}</span>
          </div>
        )}
        {selectedCommit.stats && (
          <>
            <div className="detail-row">
              <span className="detail-label">Total Changes:</span>
              <span className="detail-value">
                +{selectedCommit.stats.total.additions} -{selectedCommit.stats.total.deletions}
              </span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Files Changed:</span>
              <span className="detail-value">{selectedCommit.stats.files.length}</span>
            </div>
            <div className="detail-row">
              <span className="detail-label">Changed Files:</span>
              <div className="detail-value">
                {selectedCommit.stats.files.map((file, index) => (
                  <div key={index} className="file-change">
                    <span className="filename">{file.filename}</span>
                    <span className="file-stats">
                      +{file.additions} -{file.deletions}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="commit-history-loading">
        <div className="spinner"></div>
        <p>Loading commit history...</p>
      </div>
    );
  }

  return (
    <div className="commit-history">
      <div className="commit-history-header">
        <h2>Commit History</h2>
      </div>

      <div className="commit-history-content">
        <div className="timeline-container">
          {renderTimeline()}
        </div>
        <div className="details-panel">
          {renderCommitDetails()}
        </div>
      </div>
    </div>
  );
}

export default CommitHistory;
