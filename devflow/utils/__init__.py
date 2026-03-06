"""
Utility functions for DevFlow.
"""

import subprocess
import time
from typing import List, Dict, Any, Optional
from pathlib import Path


def run_command(command: List[str], capture_output: bool = True,
                check: bool = True, timeout: int = None) -> subprocess.CompletedProcess:
    """
    Run a shell command.

    Args:
        command: Command and arguments as a list
        capture_output: Whether to capture stdout and stderr
        check: Whether to raise an exception on non-zero exit code
        timeout: Timeout in seconds

    Returns:
        CompletedProcess object
    """
    return subprocess.run(
        command,
        capture_output=capture_output,
        check=check,
        timeout=timeout,
        text=True
    )


def check_command_exists(command: str) -> bool:
    """Check if a command exists on the system."""
    try:
        subprocess.run(
            ["which", command],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are installed."""
    dependencies = {
        "tmux": check_command_exists("tmux"),
        "git": check_command_exists("git"),
        "python3": check_command_exists("python3"),
    }

    return dependencies


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to human-readable string."""
    from datetime import datetime

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def sanitize_name(name: str) -> str:
    """Sanitize a name for use in file paths or identifiers."""
    import re

    # Replace spaces and special characters with hyphens
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', name)

    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)

    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')

    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def create_directory(path: Path, parents: bool = True, exist_ok: bool = True):
    """Create a directory, with error handling."""
    try:
        path.mkdir(parents=parents, exist_ok=exist_ok)
    except Exception as e:
        raise RuntimeError(f"Failed to create directory {path}: {e}")


def read_file(path: Path, default: str = "") -> str:
    """Read a file, returning default if it doesn't exist."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return default
    except Exception as e:
        raise RuntimeError(f"Failed to read file {path}: {e}")


def write_file(path: Path, content: str, parents: bool = True):
    """Write content to a file, creating directories if needed."""
    try:
        if parents:
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content)
    except Exception as e:
        raise RuntimeError(f"Failed to write file {path}: {e}")


def load_json(path: Path, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """Load JSON from file, returning default if it doesn't exist."""
    import json

    if default is None:
        default = {}

    try:
        if path.exists():
            return json.loads(path.read_text())
        return default
    except Exception as e:
        raise RuntimeError(f"Failed to load JSON from {path}: {e}")


def save_json(path: Path, data: Dict[str, Any], parents: bool = True):
    """Save data to JSON file."""
    import json

    try:
        if parents:
            path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to save JSON to {path}: {e}")


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple dictionaries recursively."""
    result = {}

    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value

    return result


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry(func, max_attempts: int = 3, delay: float = 1.0,
          backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Retry a function with exponential backoff."""
    import time

    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            if attempt == max_attempts - 1:
                raise

            wait_time = delay * (backoff ** attempt)
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)


def validate_project_name(name: str) -> bool:
    """Validate a project name."""
    import re

    # Project name should be alphanumeric with hyphens and underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name))


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}-{unique_id}" if prefix else unique_id
