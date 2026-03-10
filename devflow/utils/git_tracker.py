"""
Git Commit Tracker - Tracks git commits made during development.

Monitors and records git commits with associated task and agent context.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

from ..config.settings import settings


class CommitType(Enum):
    """Types of commits."""
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    TEST = "test"
    DOC = "doc"
    CHORE = "chore"
    AUTO = "auto"


class GitTracker:
    """
    Tracks git commits made during DevFlow operations.

    Maintains records of:
    - All commits with metadata
    - Associated tasks and agents
    - Files changed
    - Branch information
    """

    def __init__(self):
        self.commits_file = settings.state_dir / "git_commits.json"
        self.lock = threading.Lock()

        # Commit storage
        self.commits: Dict[str, Dict[str, Any]] = {}
        self.commit_by_task: Dict[str, List[str]] = {}  # task_id -> commit hashes
        self.commit_by_agent: Dict[str, List[str]] = {}  # agent_id -> commit hashes

        # Load existing data if available
        self.load()

    def record_commit(self, commit_hash: str, message: str, author: str,
                     branch: str, files_changed: List[str] = None,
                     commit_type: CommitType = CommitType.AUTO,
                     task_id: str = None, agent_id: str = None,
                     lines_added: int = 0, lines_deleted: int = 0):
        """
        Record a new git commit.

        Args:
            commit_hash: Full commit hash
            message: Commit message
            author: Commit author
            branch: Branch name
            files_changed: List of files changed in commit
            commit_type: Type of commit (feature, bugfix, etc.)
            task_id: Associated task ID (if any)
            agent_id: Associated agent ID (if any)
            lines_added: Number of lines added
            lines_deleted: Number of lines deleted
        """
        with self.lock:
            # Avoid duplicate commits
            if commit_hash in self.commits:
                return

            self.commits[commit_hash] = {
                "hash": commit_hash,
                "short_hash": commit_hash[:7],
                "message": message,
                "author": author,
                "branch": branch,
                "files_changed": files_changed or [],
                "commit_type": commit_type.value,
                "task_id": task_id,
                "agent_id": agent_id,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Index by task and agent
            if task_id:
                if task_id not in self.commit_by_task:
                    self.commit_by_task[task_id] = []
                self.commit_by_task[task_id].append(commit_hash)

            if agent_id:
                if agent_id not in self.commit_by_agent:
                    self.commit_by_agent[agent_id] = []
                self.commit_by_agent[agent_id].append(commit_hash)

            self.save()

    def get_commit(self, commit_hash: str) -> Optional[Dict[str, Any]]:
        """Get a specific commit by hash."""
        return self.commits.get(commit_hash)

    def get_commits_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all commits for a specific task."""
        commit_hashes = self.commit_by_task.get(task_id, [])
        return [self.commits[h] for h in commit_hashes if h in self.commits]

    def get_commits_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all commits by a specific agent."""
        commit_hashes = self.commit_by_agent.get(agent_id, [])
        return [self.commits[h] for h in commit_hashes if h in self.commits]

    def get_commits_by_branch(self, branch: str) -> List[Dict[str, Any]]:
        """Get all commits for a specific branch."""
        return [commit for commit in self.commits.values()
                if commit["branch"] == branch]

    def get_recent_commits(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent commits sorted by timestamp."""
        commits = list(self.commits.values())
        commits.sort(key=lambda x: x["timestamp"], reverse=True)
        return commits[:limit]

    def get_commits_by_type(self, commit_type: CommitType) -> List[Dict[str, Any]]:
        """Get all commits of a specific type."""
        return [commit for commit in self.commits.values()
                if commit["commit_type"] == commit_type.value]

    def get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all commits that touched a specific file."""
        return [commit for commit in self.commits.values()
                if file_path in commit.get("files_changed", [])]

    def get_commit_stats(self) -> Dict[str, Any]:
        """Get statistics about commits."""
        with self.lock:
            total_commits = len(self.commits)
            total_lines_added = sum(c.get("lines_added", 0) for c in self.commits.values())
            total_lines_deleted = sum(c.get("lines_deleted", 0) for c in self.commits.values())

            # Count by type
            type_counts = {}
            for commit in self.commits.values():
                ctype = commit.get("commit_type", "unknown")
                type_counts[ctype] = type_counts.get(ctype, 0) + 1

            # Count by branch
            branch_counts = {}
            for commit in self.commits.values():
                branch = commit.get("branch", "unknown")
                branch_counts[branch] = branch_counts.get(branch, 0) + 1

            return {
                "total_commits": total_commits,
                "total_lines_added": total_lines_added,
                "total_lines_deleted": total_lines_deleted,
                "net_lines": total_lines_added - total_lines_deleted,
                "by_type": type_counts,
                "by_branch": branch_counts,
                "recent_commit": self.get_recent_commits(1)[0] if total_commits > 0 else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def search_commits(self, query: str) -> List[Dict[str, Any]]:
        """Search commits by message or files changed."""
        query_lower = query.lower()
        results = []

        for commit in self.commits.values():
            # Search in message
            if query_lower in commit.get("message", "").lower():
                results.append(commit)
                continue

            # Search in files
            files = commit.get("files_changed", [])
            if any(query_lower in f.lower() for f in files):
                results.append(commit)
                continue

        return results

    def get_commit_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get commits within the last N hours."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()

        return [commit for commit in self.commits.values()
                if commit.get("timestamp", "") >= cutoff_iso]

    def save(self):
        """Save commit data to disk."""
        self.commits_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "commits": self.commits,
            "commit_by_task": self.commit_by_task,
            "commit_by_agent": self.commit_by_agent,
        }

        with open(self.commits_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load(self):
        """Load commit data from disk."""
        if self.commits_file.exists():
            with open(self.commits_file, 'r') as f:
                data = json.load(f)

            self.commits = data.get("commits", {})
            self.commit_by_task = data.get("commit_by_task", {})
            self.commit_by_agent = data.get("commit_by_agent", {})

    def reset(self):
        """Reset all commit tracking data."""
        with self.lock:
            self.commits.clear()
            self.commit_by_task.clear()
            self.commit_by_agent.clear()
            self.save()
