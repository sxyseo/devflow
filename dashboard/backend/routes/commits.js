/**
 * DevFlow Dashboard Backend - Commits Route
 *
 * API endpoints for retrieving git commit history.
 */

const express = require('express');
const { exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

const router = express.Router();

/**
 * GET /api/commits
 *
 * Retrieve git commit history for the DevFlow repository.
 * Query parameters:
 * - limit: Number of commits to return (default: 20)
 * - branch: Git branch to query (default: current branch)
 */
router.get('/', async (req, res) => {
  try {
    const { limit = 20, branch } = req.query;
    const commitsLimit = parseInt(limit, 10) || 20;

    // Get the repository root directory (assuming .git is in project root)
    const repoRoot = path.join(__dirname, '../../../');

    // Build git log command
    let gitCommand = `cd "${repoRoot}" && git log -${commitsLimit} --pretty=format:'%H|%an|%ae|%ad|%s|%b' --date=iso`;

    if (branch) {
      gitCommand = `cd "${repoRoot}" && git log ${branch} -${commitsLimit} --pretty=format:'%H|%an|%ae|%ad|%s|%b' --date=iso`;
    }

    // Execute git command
    exec(gitCommand, { maxBuffer: 1024 * 1024 * 10 }, async (error, stdout, stderr) => {
      if (error) {
        // If git is not available or repository doesn't exist, return mock data
        if (error.message.includes('not a git repository') || error.code === 128) {
          return res.json(getMockCommits(commitsLimit));
        }
        return res.status(500).json({ error: 'Failed to retrieve commit history', details: error.message });
      }

      if (stderr && !stderr.includes('fatal')) {
        // Some warnings in stderr are okay
      }

      // Parse git output
      const commits = parseCommits(stdout);

      // Enhance with file change statistics
      const enrichedCommits = await enrichCommitsWithStats(commits, repoRoot);

      res.json(enrichedCommits);
    });

  } catch (error) {
    res.status(500).json({ error: 'Internal server error', details: error.message });
  }
});

/**
 * Parse git log output into structured commit objects
 */
function parseCommits(gitOutput) {
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
      },
      stats: null
    };
  });
}

/**
 * Enrich commits with file change statistics
 */
async function enrichCommitsWithStats(commits, repoRoot) {
  const enriched = [];

  for (const commit of commits) {
    try {
      const stats = await getCommitStats(commit.hash, repoRoot);
      enriched.push({ ...commit, stats });
    } catch (error) {
      // If stats retrieval fails, still include the commit without stats
      enriched.push(commit);
    }
  }

  return enriched;
}

/**
 * Get file change statistics for a specific commit
 */
function getCommitStats(commitHash, repoRoot) {
  return new Promise((resolve, reject) => {
    const gitCommand = `cd "${repoRoot}" && git show --stat --format='' ${commitHash}`;

    exec(gitCommand, { maxBuffer: 1024 * 1024 * 5 }, (error, stdout, stderr) => {
      if (error) {
        return resolve(null);
      }

      // Parse git stat output
      const stats = parseGitStats(stdout);
      resolve(stats);
    });
  });
}

/**
 * Parse git show --stat output
 */
function parseGitStats(statsOutput) {
  if (!statsOutput || statsOutput.trim() === '') {
    return null;
  }

  const lines = statsOutput.trim().split('\n');
  const files = [];
  let totalAdditions = 0;
  let totalDeletions = 0;

  for (const line of lines) {
    // Match lines like: " file.txt    | 10 +++++-----
    const match = line.match(/^\s*(.+?)\s*\|\s*(\d+)\s*([\+\+\+]+\s*[\-\-\-]+)?/);
    if (match) {
      const filename = match[1].trim();
      const changes = parseInt(match[2], 10);

      // Count additions and deletions
      const additions = (line.match(/\+/g) || []).length;
      const deletions = (line.match(/\-/g) || []).length;

      totalAdditions += additions;
      totalDeletions += deletions;

      files.push({
        filename,
        changes,
        additions,
        deletions
      });
    }
  }

  return {
    files,
    total: {
      additions: totalAdditions,
      deletions: totalDeletions,
      changes: totalAdditions + totalDeletions
    }
  };
}

/**
 * Generate mock commits for when git is not available
 */
function getMockCommits(limit) {
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
        subject: 'feat: Add commit history API endpoint',
        body: 'Implement GET /api/commits endpoint to retrieve git commit history'
      },
      stats: {
        files: [
          { filename: 'dashboard/backend/routes/commits.js', changes: 150, additions: 120, deletions: 30 }
        ],
        total: { additions: 120, deletions: 30, changes: 150 }
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
        subject: 'fix: Resolve memory leak in agent executor',
        body: 'Fixed issue where agent processes were not properly cleaned up'
      },
      stats: {
        files: [
          { filename: 'prod/agents/executor.js', changes: 45, additions: 30, deletions: 15 }
        ],
        total: { additions: 30, deletions: 15, changes: 45 }
      }
    },
    {
      hash: 'c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2',
      shortHash: 'c3d4e5f',
      author: {
        name: 'Auto Claude',
        email: 'auto-claude@devflow.local'
      },
      date: new Date(Date.now() - 7200000).toISOString(),
      message: {
        subject: 'refactor: Improve workflow orchestration',
        body: 'Restructured workflow execution to support parallel task processing'
      },
      stats: {
        files: [
          { filename: 'prod/orchestrator/workflow.js', changes: 80, additions: 60, deletions: 20 },
          { filename: 'prod/orchestrator/scheduler.js', changes: 35, additions: 25, deletions: 10 }
        ],
        total: { additions: 85, deletions: 30, changes: 115 }
      }
    }
  ];

  return mockCommits.slice(0, limit);
}

module.exports = router;
