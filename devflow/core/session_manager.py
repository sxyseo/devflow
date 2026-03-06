"""
Session Manager - Manages agent sessions using tmux.

Creates, monitors, and cleans up tmux sessions for background agent execution.
"""

import subprocess
import threading
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..config.settings import settings


@dataclass
class SessionInfo:
    """Information about a tmux session."""
    name: str
    agent_type: str
    agent_id: str
    created_at: str
    pid: Optional[int] = None
    status: str = "running"


class SessionManager:
    """
    Manages tmux sessions for background agent execution.

    Provides:
    - Session creation and cleanup
    - Session monitoring
    - Output capture
    - Automatic session recovery
    """

    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}
        self.lock = threading.Lock()
        self._monitor_thread = None
        self._running = False

    def start_monitoring(self):
        """Start background session monitoring."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_sessions, daemon=True)
            self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop background session monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None

    def create_session(self, agent_id: str, agent_type: str,
                      task: str, window_name: str = None) -> SessionInfo:
        """
        Create a new tmux session for an agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (e.g., 'planning', 'development')
            task: Task description to execute
            window_name: Optional window name

        Returns:
            SessionInfo object with session details
        """
        session_name = f"{settings.tmux_session_prefix}{agent_type}-{agent_id}"
        window_name = window_name or agent_id

        # Create session with initial window
        cmd = [
            "tmux", "new-session",
            "-d", "-s", session_name,
            "-n", window_name,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create tmux session: {result.stderr}")

        # Send task to session
        self.send_command(session_name, task)

        # Create session info
        session_info = SessionInfo(
            name=session_name,
            agent_type=agent_type,
            agent_id=agent_id,
            created_at=time.time(),
        )

        with self.lock:
            self.sessions[session_name] = session_info

        return session_info

    def send_command(self, session_name: str, command: str):
        """Send a command to a tmux session."""
        cmd = [
            "tmux", "send-keys",
            "-t", session_name,
            command,
            "C-m"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to send command to session: {result.stderr}")

    def get_session_output(self, session_name: str, lines: int = 100) -> str:
        """Capture output from a tmux session."""
        cmd = [
            "tmux", "capture-pane",
            "-t", session_name,
            "-p", "-S", f"-{lines}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return f"Error capturing output: {result.stderr}"

        return result.stdout

    def session_exists(self, session_name: str) -> bool:
        """Check if a tmux session exists."""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", session_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def kill_session(self, session_name: str):
        """Kill a tmux session."""
        cmd = ["tmux", "kill-session", "-t", session_name]
        subprocess.run(cmd, capture_output=True, text=True)

        with self.lock:
            if session_name in self.sessions:
                del self.sessions[session_name]

    def list_sessions(self) -> List[str]:
        """List all active tmux sessions."""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                check=True
            )

            sessions = result.stdout.strip().split('\n')
            return [s for s in sessions if s.startswith(settings.tmux_session_prefix)]

        except subprocess.CalledProcessError:
            return []

    def get_session_info(self, session_name: str) -> Optional[SessionInfo]:
        """Get information about a session."""
        return self.sessions.get(session_name)

    def cleanup_dead_sessions(self):
        """Remove dead sessions from tracking."""
        with self.lock:
            dead_sessions = [
                name for name in self.sessions
                if not self.session_exists(name)
            ]

            for name in dead_sessions:
                del self.sessions[name]

            return len(dead_sessions)

    def cleanup_all_sessions(self):
        """Kill all DevFlow tmux sessions."""
        sessions = self.list_sessions()

        for session_name in sessions:
            self.kill_session(session_name)

    def _monitor_sessions(self):
        """Background thread to monitor sessions."""
        while self._running:
            try:
                self.cleanup_dead_sessions()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Session monitor error: {e}")
                time.sleep(60)

    def attach_session(self, session_name: str):
        """Attach to a session (interactive)."""
        if not self.session_exists(session_name):
            raise ValueError(f"Session {session_name} does not exist")

        subprocess.run(["tmux", "attach-session", "-t", session_name])

    def get_active_sessions(self) -> Dict[str, SessionInfo]:
        """Get all active sessions."""
        with self.lock:
            return self.sessions.copy()
