"""
Response Cache - File-based caching for API responses.

Provides intelligent caching with hash-based key generation,
TTL support, and persistent storage.
"""

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List

from .base import CacheBackend, CacheEntry
from ..config.settings import settings


class ResponseCache(CacheBackend):
    """
    File-based cache for API responses.

    Features:
    - Hash-based cache key generation
    - Persistent file storage
    - TTL support with expiration checking
    - Thread-safe operations
    - Cache statistics tracking

    Storage structure:
    .devflow/cache/
      ├── cache_index.json      # Index of all cache entries
      └── entries/              # Individual cache entries
          └── {hash}.json       # Cache entry data
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the response cache.

        Args:
            cache_dir: Custom cache directory (defaults to .devflow/cache)
        """
        super().__init__()

        if cache_dir is None:
            self.cache_dir = settings.project_root / ".devflow" / "cache"
        else:
            self.cache_dir = cache_dir

        self.entries_dir = self.cache_dir / "entries"
        self.index_file = self.cache_dir / "cache_index.json"

        # In-memory index for fast lookups
        self.index: Dict[str, Dict[str, Any]] = {}

        # Load existing index
        self.load_index()

    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.

        Creates a deterministic hash key from the provided arguments.
        Useful for caching function call results.

        Args:
            *args: Positional arguments to hash
            **kwargs: Keyword arguments to hash

        Returns:
            Hexadecimal hash string
        """
        # Create a deterministic string representation
        key_parts = []

        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, dict):
                key_parts.append(json.dumps(arg, sort_keys=True))
            elif isinstance(arg, list):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                # For other types, use repr
                key_parts.append(repr(arg))

        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}={value}")
            elif isinstance(value, dict):
                key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
            elif isinstance(value, list):
                key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
            else:
                key_parts.append(f"{key}={repr(value)}")

        # Join and hash
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            # Check if key exists in index
            if key not in self.index:
                self._record_miss()
                return None

            entry_data = self.index[key]

            # Check if expired
            if self._is_expired(entry_data):
                self.delete(key)
                self._record_miss()
                return None

            # Load the entry from disk
            entry_file = self.entries_dir / f"{key}.json"
            if not entry_file.exists():
                self._record_miss()
                return None

            try:
                with open(entry_file, 'r') as f:
                    entry = json.load(f)

                # Update access count
                entry_data["access_count"] += 1
                entry_data["last_accessed_at"] = datetime.utcnow().isoformat()
                self.save_index()

                self._record_hit()
                return entry.get("value")
            except (json.JSONDecodeError, IOError):
                self._record_miss()
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a value in the cache.

        Args:
            key: Cache key to store under
            value: Value to cache
            ttl: Time to live in seconds (None = no expiration)
            metadata: Optional metadata about the cached item

        Returns:
            True if successfully stored
        """
        with self.lock:
            try:
                # Ensure directories exist
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.entries_dir.mkdir(parents=True, exist_ok=True)

                # Create cache entry
                now = datetime.utcnow().isoformat()
                entry = {
                    "key": key,
                    "value": value,
                    "ttl": ttl,
                    "created_at": now,
                    "updated_at": now,
                    "access_count": 0,
                    "last_accessed_at": now,
                    "metadata": metadata or {},
                }

                # Write to disk
                entry_file = self.entries_dir / f"{key}.json"
                with open(entry_file, 'w') as f:
                    json.dump(entry, f, indent=2, default=str)

                # Update index
                self.index[key] = {
                    "created_at": now,
                    "expires_at": self._calculate_expires_at(ttl, now),
                    "access_count": 0,
                    "last_accessed_at": now,
                    "metadata": metadata or {},
                }

                self.save_index()
                self._record_set()
                return True
            except (IOError, OSError):
                return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was found and deleted
        """
        with self.lock:
            if key not in self.index:
                return False

            try:
                # Remove entry file
                entry_file = self.entries_dir / f"{key}.json"
                if entry_file.exists():
                    entry_file.unlink()

                # Remove from index
                del self.index[key]
                self.save_index()

                self._record_delete()
                return True
            except (IOError, OSError):
                return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists and is not expired
        """
        with self.lock:
            if key not in self.index:
                return False

            # Check if expired
            entry_data = self.index[key]
            if self._is_expired(entry_data):
                return False

            return True

    def clear(self):
        """Clear all entries from the cache."""
        with self.lock:
            try:
                # Remove all entry files
                if self.entries_dir.exists():
                    for entry_file in self.entries_dir.glob("*.json"):
                        entry_file.unlink()

                # Clear index
                self.index.clear()
                self.save_index()
            except (IOError, OSError):
                pass

    def get_size(self) -> int:
        """
        Get the number of entries in the cache.

        Returns:
            Number of cached entries
        """
        with self.lock:
            # Count only non-expired entries
            count = 0
            for key, entry_data in self.index.items():
                if not self._is_expired(entry_data):
                    count += 1
            return count

    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: Optional glob pattern to match keys

        Returns:
            List of cache keys
        """
        with self.lock:
            keys = list(self.index.keys())

            if pattern:
                # Simple glob-style pattern matching
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]

            return keys

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        with self.lock:
            removed = 0
            expired_keys = []

            # Find expired keys
            for key, entry_data in self.index.items():
                if self._is_expired(entry_data):
                    expired_keys.append(key)

            # Remove expired entries
            for key in expired_keys:
                if self.delete(key):
                    removed += 1

            return removed

    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a cache entry.

        Args:
            key: Cache key to query

        Returns:
            Entry metadata or None if not found
        """
        with self.lock:
            if key not in self.index:
                return None

            entry_data = self.index[key].copy()
            entry_data["key"] = key
            entry_data["expired"] = self._is_expired(entry_data)
            return entry_data

    def get_cache_size_bytes(self) -> int:
        """
        Get the total disk size of the cache.

        Returns:
            Size in bytes
        """
        try:
            if not self.entries_dir.exists():
                return 0

            total_size = 0
            for entry_file in self.entries_dir.glob("*.json"):
                total_size += entry_file.stat().st_size

            return total_size
        except (IOError, OSError):
            return 0

    def _calculate_expires_at(self, ttl: Optional[int], created_at: str) -> Optional[str]:
        """Calculate expiration timestamp."""
        if ttl is None:
            return None

        created = datetime.fromisoformat(created_at)
        from datetime import timedelta
        expires = created + timedelta(seconds=ttl)
        return expires.isoformat()

    def _is_expired(self, entry_data: Dict[str, Any]) -> bool:
        """Check if an entry is expired."""
        expires_at = entry_data.get("expires_at")
        if expires_at is None:
            return False

        expires = datetime.fromisoformat(expires_at)
        return datetime.utcnow() > expires

    def load_index(self):
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.index = {}
        else:
            self.index = {}

    def save_index(self):
        """Save cache index to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2, default=str)
        except (IOError, OSError):
            pass
