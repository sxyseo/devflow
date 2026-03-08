"""
Base Cache Backend - Abstract interface for cache implementations.

Defines the common interface that all cache backends must implement.
"""

import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from datetime import timedelta
from pathlib import Path


class CacheEntry:
    """
    Represents a single cache entry.

    Attributes:
        key: Unique cache key
        value: Cached value
        ttl: Time to live in seconds (None = no expiration)
        created_at: Timestamp when entry was created
        access_count: Number of times this entry was accessed
        metadata: Optional metadata about the cached item
    """

    def __init__(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a cache entry."""
        from datetime import datetime

        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = datetime.utcnow().isoformat()
        self.access_count = 0
        self.metadata = metadata or {}

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.ttl is None:
            return False

        from datetime import datetime
        created = datetime.fromisoformat(self.created_at)
        elapsed = (datetime.utcnow() - created).total_seconds()
        return elapsed > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "ttl": self.ttl,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "metadata": self.metadata,
        }


class CacheBackend(ABC):
    """
    Abstract base class for cache backends.

    Defines the interface that all cache implementations must follow.
    Supports:
    - Key-value caching with TTL
    - Thread-safe operations
    - Cache statistics
    - Bulk operations
    """

    def __init__(self):
        """Initialize the cache backend."""
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value or None if not found/expired
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was found and deleted
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists and is not expired
        """
        pass

    @abstractmethod
    def clear(self):
        """Clear all entries from the cache."""
        pass

    @abstractmethod
    def get_size(self) -> int:
        """
        Get the number of entries in the cache.

        Returns:
            Number of cached entries
        """
        pass

    @abstractmethod
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: Optional glob pattern to match keys

        Returns:
            List of cache keys
        """
        pass

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple values from the cache.

        Args:
            keys: List of cache keys to retrieve

        Returns:
            Dictionary mapping keys to their values
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: Dict[str, Any],
                 ttl: Optional[int] = None) -> bool:
        """
        Store multiple values in the cache.

        Args:
            mapping: Dictionary of key-value pairs to cache
            ttl: Default time to live in seconds

        Returns:
            True if all values were successfully stored
        """
        success = True
        for key, value in mapping.items():
            if not self.set(key, value, ttl=ttl):
                success = False
        return success

    def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys from the cache.

        Args:
            keys: List of cache keys to delete

        Returns:
            Number of keys that were deleted
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        keys = self.get_keys()
        removed = 0
        for key in keys:
            # Check if entry exists (will be False if expired)
            if not self.exists(key):
                self.delete(key)
                removed += 1
        return removed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary containing cache metrics
        """
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"],
                "evictions": self.stats["evictions"],
                "hit_rate": hit_rate,
                "size": self.get_size(),
            }

    def reset_stats(self):
        """Reset cache statistics."""
        with self.lock:
            for key in self.stats:
                self.stats[key] = 0

    def _record_hit(self):
        """Record a cache hit."""
        with self.lock:
            self.stats["hits"] += 1

    def _record_miss(self):
        """Record a cache miss."""
        with self.lock:
            self.stats["misses"] += 1

    def _record_set(self):
        """Record a cache set operation."""
        with self.lock:
            self.stats["sets"] += 1

    def _record_delete(self):
        """Record a cache delete operation."""
        with self.lock:
            self.stats["deletes"] += 1

    def _record_eviction(self):
        """Record a cache eviction."""
        with self.lock:
            self.stats["evictions"] += 1
