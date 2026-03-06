"""
Git Worktree Manager - Manage git worktrees for isolated development.

Creates, manages, and cleans up git worktrees for parallel isolated development.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
import re


@dataclass
class WorktreeInfo:
    """Information about a worktree."""
    path: Path
    branch: str
    commit: str
    is_bare: bool = False
    is_detached: bool = False
    created_at: float = None
    last_used: float = None


class GitWorktreeManager:
    """
    Manages git worktrees for isolated parallel development.

    Features:
    - Create worktrees for branches or commits
    - List and query worktrees
    - Clean up old worktrees
    - Execute commands in worktrees
    - Prune stale worktrees
    """

    def __init__(self, repo_root: Path = None, worktrees_dir: Path = None):
        self.repo_root = repo_root or Path.cwd()
        self.worktrees_dir = worktrees_dir or Path("/tmp/devflow-worktrees")

        # Ensure worktrees directory exists
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        # Verify we're in a git repo
        if not self._is_git_repo():
            raise RuntimeError(f"Not a git repository: {self.repo_root}")

    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        git_dir = self.repo_root / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def _run_git(self, args: List[str], capture_output: bool = True,
                 check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        cmd = ["git"] + args

        if capture_output:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                cwd=self.repo_root
            )
        else:
            result = subprocess.run(
                cmd,
                check=check,
                cwd=self.repo_root
            )

        return result

    def create_worktree(self, branch_name: str, base_branch: str = "main",
                       worktree_name: str = None) -> WorktreeInfo:
        """
        Create a new git worktree.

        Args:
            branch_name: Name for the new branch
            base_branch: Base branch to create from
            worktree_name: Optional custom worktree directory name

        Returns:
            WorktreeInfo object
        """
        # Generate worktree path
        if worktree_name:
            worktree_path = self.worktrees_dir / worktree_name
        else:
            worktree_path = self.worktrees_dir / branch_name

        # Check if worktree already exists
        if worktree_path.exists():
            raise ValueError(f"Worktree path already exists: {worktree_path}")

        # Ensure base branch exists
        try:
            self._run_git(["rev-parse", "--verify", base_branch])
        except subprocess.CalledProcessError:
            raise RuntimeError(f"Base branch '{base_branch}' does not exist")

        # Create worktree
        try:
            self._run_git([
                "worktree", "add",
                "-b", branch_name,
                str(worktree_path),
                base_branch
            ])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create worktree: {e.stderr}")

        # Get worktree info
        worktree_info = self.get_worktree_info(worktree_path)
        worktree_info.created_at = time.time()

        return worktree_info

    def create_detached_worktree(self, commit: str, worktree_name: str) -> WorktreeInfo:
        """
        Create a detached worktree at a specific commit.

        Args:
            commit: Commit hash or reference
            worktree_name: Worktree directory name

        Returns:
            WorktreeInfo object
        """
        worktree_path = self.worktrees_dir / worktree_name

        if worktree_path.exists():
            raise ValueError(f"Worktree path already exists: {worktree_path}")

        # Create detached worktree
        try:
            self._run_git([
                "worktree", "add",
                "--detach",
                str(worktree_path),
                commit
            ])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create detached worktree: {e.stderr}")

        # Get worktree info
        worktree_info = self.get_worktree_info(worktree_path)
        worktree_info.created_at = time.time()
        worktree_info.is_detached = True

        return worktree_info

    def get_worktree_info(self, worktree_path: Path) -> WorktreeInfo:
        """Get information about a worktree."""
        try:
            # Get worktree list
            result = self._run_git(["worktree", "list", "--porcelain"])

            # Parse output
            current_worktree = None
            branch = None
            commit = None
            is_bare = False
            is_detached = False

            for line in result.stdout.split('\n'):
                line = line.strip()

                if line.startswith("worktree "):
                    if current_worktree and Path(current_worktree) == worktree_path:
                        # Found our worktree
                        break

                    current_worktree = line[9:].strip()
                    branch = None
                    commit = None
                    is_bare = False
                    is_detached = False

                elif line.startswith("branch "):
                    branch = line[7:].strip()
                    branch = branch.replace("refs/heads/", "")

                elif line.startswith("HEAD "):
                    commit = line[5:].strip()

                elif line.startswith("detached"):
                    is_detached = True

                elif line.startswith("bare"):
                    is_bare = True

            if not current_worktree or Path(current_worktree) != worktree_path:
                raise ValueError(f"Worktree not found: {worktree_path}")

            return WorktreeInfo(
                path=worktree_path,
                branch=branch,
                commit=commit,
                is_bare=is_bare,
                is_detached=is_detached
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get worktree info: {e.stderr}")

    def list_worktrees(self) -> List[WorktreeInfo]:
        """List all worktrees."""
        try:
            result = self._run_git(["worktree", "list", "--porcelain"])

            worktrees = []
            current_worktree = None
            branch = None
            commit = None
            is_bare = False
            is_detached = False

            for line in result.stdout.split('\n'):
                line = line.strip()

                if line.startswith("worktree "):
                    # Save previous worktree if exists
                    if current_worktree:
                        worktrees.append(WorktreeInfo(
                            path=Path(current_worktree),
                            branch=branch,
                            commit=commit,
                            is_bare=is_bare,
                            is_detached=is_detached
                        ))

                    # Start new worktree
                    current_worktree = line[9:].strip()
                    branch = None
                    commit = None
                    is_bare = False
                    is_detached = False

                elif line.startswith("branch "):
                    branch = line[7:].strip()
                    branch = branch.replace("refs/heads/", "")

                elif line.startswith("HEAD "):
                    commit = line[5:].strip()

                elif line.startswith("detached"):
                    is_detached = True

                elif line.startswith("bare"):
                    is_bare = True

            # Add last worktree
            if current_worktree:
                worktrees.append(WorktreeInfo(
                    path=Path(current_worktree),
                    branch=branch,
                    commit=commit,
                    is_bare=is_bare,
                    is_detached=is_detached
                ))

            return worktrees

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to list worktrees: {e.stderr}")

    def remove_worktree(self, worktree_path: Path, force: bool = False) -> bool:
        """
        Remove a worktree.

        Args:
            worktree_path: Path to the worktree
            force: Force removal even if there are uncommitted changes

        Returns:
            True if removed successfully
        """
        try:
            args = ["worktree", "remove"]

            if force:
                args.append("--force")

            args.append(str(worktree_path))

            self._run_git(args)
            return True

        except subprocess.CalledProcessError as e:
            print(f"Failed to remove worktree: {e.stderr}")
            return False

    def prune_worktrees(self) -> int:
        """
        Prune stale worktrees.

        Removes worktree directories that no longer exist.

        Returns:
            Number of worktrees pruned
        """
        try:
            result = self._run_git(["worktree", "prune"])
            return 0  # Git doesn't tell us how many were pruned
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to prune worktrees: {e.stderr}")

    def cleanup_old_worktrees(self, max_age_days: int = 7) -> List[Path]:
        """
        Clean up old worktrees.

        Args:
            max_age_days: Maximum age in days before a worktree is considered old

        Returns:
            List of cleaned up worktree paths
        """
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        cleaned_up = []

        # List all worktrees
        worktrees = self.list_worktrees()

        for worktree in worktrees:
            # Skip main repo worktree
            if worktree.path == self.repo_root:
                continue

            # Check if worktree directory exists
            if not worktree.path.exists():
                # Prune it
                self.prune_worktrees()
                cleaned_up.append(worktree.path)
                continue

            # Check age
            try:
                stat = worktree.path.stat()
                age = current_time - stat.st_mtime

                if age > max_age_seconds:
                    # Remove old worktree
                    if self.remove_worktree(worktree.path, force=True):
                        cleaned_up.append(worktree.path)
            except Exception as e:
                print(f"Warning: Could not check age of {worktree.path}: {e}")

        return cleaned_up

    def execute_in_worktree(self, worktree_path: Path, command: List[str],
                           capture_output: bool = True) -> subprocess.CompletedProcess:
        """
        Execute a command in a worktree.

        Args:
            worktree_path: Path to the worktree
            command: Command to execute
            capture_output: Whether to capture output

        Returns:
            CompletedProcess result
        """
        if not worktree_path.exists():
            raise ValueError(f"Worktree does not exist: {worktree_path}")

        return subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            cwd=worktree_path
        )

    def get_worktree_status(self, worktree_path: Path) -> Dict[str, Any]:
        """Get status of a worktree."""
        try:
            # Run git status
            result = self.execute_in_worktree(
                worktree_path,
                ["git", "status", "--porcelain"]
            )

            # Parse output
            changes = result.stdout.strip().split('\n') if result.stdout.strip() else []

            staged = [line for line in changes if line.startswith(' ')]
            modified = [line for line in changes if line.startswith(' M')]
            untracked = [line for line in changes if line.startswith('??')]

            return {
                "path": str(worktree_path),
                "staged_count": len(staged),
                "modified_count": len(modified),
                "untracked_count": len(untracked),
                "has_changes": len(changes) > 0,
                "is_clean": len(changes) == 0,
            }

        except Exception as e:
            return {
                "path": str(worktree_path),
                "error": str(e),
                "has_changes": False,
                "is_clean": False,
            }

    def commit_in_worktree(self, worktree_path: Path, message: str,
                          add_all: bool = True) -> bool:
        """
        Commit changes in a worktree.

        Args:
            worktree_path: Path to the worktree
            message: Commit message
            add_all: Whether to add all changes before committing

        Returns:
            True if committed successfully
        """
        try:
            # Add changes
            if add_all:
                self.execute_in_worktree(worktree_path, ["git", "add", "-A"])

            # Commit
            result = self.execute_in_worktree(
                worktree_path,
                ["git", "commit", "-m", message]
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Failed to commit in worktree: {e}")
            return False

    def push_worktree_branch(self, worktree_path: Path, remote: str = "origin") -> bool:
        """
        Push worktree branch to remote.

        Args:
            worktree_path: Path to the worktree
            remote: Remote name

        Returns:
            True if pushed successfully
        """
        try:
            # Get worktree info to get branch name
            info = self.get_worktree_info(worktree_path)

            if not info.branch:
                raise ValueError("Worktree has no branch (detached HEAD)")

            # Push branch
            result = self.execute_in_worktree(
                worktree_path,
                ["git", "push", "-u", remote, info.branch]
            )

            return result.returncode == 0

        except Exception as e:
            print(f"Failed to push worktree branch: {e}")
            return False
