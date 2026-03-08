"""
Prompt Optimizer - Token counting and prompt compression.

Optimizes prompts to reduce token usage and API costs.
"""

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from .base import CacheBackend
from ..config.settings import settings


@dataclass
class PromptStats:
    """Statistics about a prompt."""
    original_tokens: int
    optimized_tokens: int
    compression_ratio: float
    optimizations_applied: List[str] = field(default_factory=list)


@dataclass
class OptimizerConfig:
    """Configuration for prompt optimization."""
    max_tokens: int = 200000
    enable_whitespace_removal: bool = True
    enable_duplicate_removal: bool = True
    enable_template_compression: bool = True
    preserve_code_blocks: bool = True
    preserve_structure: bool = True
    enable_template_caching: bool = True


class TemplateCache(CacheBackend):
    """
    Cache for prompt templates and their optimized versions.

    Features:
    - Hash-based cache key generation from prompt content
    - Persistent file storage
    - TTL support with expiration checking
    - Thread-safe operations
    - Cache statistics tracking

    Storage structure:
    .devflow/cache/
      ├── template_index.json   # Index of template cache entries
      └── templates/            # Individual template entries
          └── {hash}.json       # Template cache entry data
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the template cache.

        Args:
            cache_dir: Custom cache directory (defaults to .devflow/cache)
        """
        super().__init__()

        if cache_dir is None:
            self.cache_dir = settings.project_root / ".devflow" / "cache"
        else:
            self.cache_dir = cache_dir

        self.templates_dir = self.cache_dir / "templates"
        self.index_file = self.cache_dir / "template_index.json"

        # In-memory index for fast lookups
        self.index: Dict[str, Dict[str, Any]] = {}

        # Load existing index
        self.load_index()

    def generate_key(self, prompt: str, config: OptimizerConfig) -> str:
        """
        Generate a cache key from prompt and configuration.

        Creates a deterministic hash key that accounts for both
        the prompt content and optimization settings.

        Args:
            prompt: The prompt to hash
            config: Optimizer configuration

        Returns:
            Hexadecimal hash string
        """
        # Create a deterministic string representation
        key_parts = [prompt]

        # Include relevant config settings that affect optimization
        config_dict = {
            "enable_whitespace_removal": config.enable_whitespace_removal,
            "enable_duplicate_removal": config.enable_duplicate_removal,
            "enable_template_compression": config.enable_template_compression,
            "preserve_code_blocks": config.preserve_code_blocks,
        }
        key_parts.append(json.dumps(config_dict, sort_keys=True))

        # Join and hash
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached template from the cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached template data or None if not found/expired
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
            template_file = self.templates_dir / f"{key}.json"
            if not template_file.exists():
                self._record_miss()
                return None

            try:
                with open(template_file, 'r') as f:
                    entry = json.load(f)

                # Update access count
                entry_data["access_count"] += 1
                entry_data["last_accessed_at"] = datetime.utcnow().isoformat()
                self.save_index()

                self._record_hit()
                return entry
            except (json.JSONDecodeError, IOError):
                self._record_miss()
                return None

    def set(self, key: str, prompt: str, optimized: str, stats: 'PromptStats',
            ttl: Optional[int] = None) -> bool:
        """
        Store a template in the cache.

        Args:
            key: Cache key to store under
            prompt: Original prompt
            optimized: Optimized prompt
            stats: Optimization statistics
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successfully stored
        """
        with self.lock:
            try:
                # Ensure directories exist
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.templates_dir.mkdir(parents=True, exist_ok=True)

                # Create cache entry
                now = datetime.utcnow().isoformat()
                entry = {
                    "key": key,
                    "prompt": prompt,
                    "optimized": optimized,
                    "original_tokens": stats.original_tokens,
                    "optimized_tokens": stats.optimized_tokens,
                    "compression_ratio": stats.compression_ratio,
                    "optimizations_applied": stats.optimizations_applied,
                    "ttl": ttl,
                    "created_at": now,
                    "updated_at": now,
                    "access_count": 0,
                    "last_accessed_at": now,
                }

                # Write to disk
                template_file = self.templates_dir / f"{key}.json"
                with open(template_file, 'w') as f:
                    json.dump(entry, f, indent=2, default=str)

                # Update index
                self.index[key] = {
                    "created_at": now,
                    "expires_at": self._calculate_expires_at(ttl, now),
                    "access_count": 0,
                    "last_accessed_at": now,
                }

                self.save_index()
                self._record_set()
                return True
            except (IOError, OSError):
                return False

    def delete(self, key: str) -> bool:
        """
        Delete a template from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was found and deleted
        """
        with self.lock:
            if key not in self.index:
                return False

            try:
                # Remove template file
                template_file = self.templates_dir / f"{key}.json"
                if template_file.exists():
                    template_file.unlink()

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
                # Remove all template files
                if self.templates_dir.exists():
                    for template_file in self.templates_dir.glob("*.json"):
                        template_file.unlink()

                # Clear index
                self.index.clear()
                self.save_index()
            except (IOError, OSError):
                pass

    def get_size(self) -> int:
        """
        Get the number of entries in the cache.

        Returns:
            Number of cached templates
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

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics.

        Returns:
            Dictionary containing cache metrics
        """
        with self.lock:
            total_entries = len(self.index)
            total_tokens_saved = 0

            # Calculate total tokens saved across all templates
            for key in self.index.keys():
                template_file = self.templates_dir / f"{key}.json"
                if template_file.exists():
                    try:
                        with open(template_file, 'r') as f:
                            entry = json.load(f)
                            tokens_saved = entry.get("original_tokens", 0) - entry.get("optimized_tokens", 0)
                            total_tokens_saved += max(0, tokens_saved)
                    except (json.JSONDecodeError, IOError):
                        pass

            return {
                "total_templates": total_entries,
                "total_tokens_saved": total_tokens_saved,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                if (self.stats["hits"] + self.stats["misses"]) > 0 else 0,
            }

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


class PromptOptimizer:
    """
    Optimizes prompts to reduce token usage.

    Responsibilities:
    - Token counting for accurate cost estimation
    - Prompt compression to reduce token usage
    - Redundancy removal
    - Template optimization
    - Statistics tracking

    Optimization Strategies:
    1. Whitespace normalization (removes excessive whitespace)
    2. Duplicate line removal
    3. Template compression (removes redundant boilerplate)
    4. Structure preservation (keeps code blocks intact)
    """

    def __init__(self, config: Optional[OptimizerConfig] = None):
        """
        Initialize the prompt optimizer.

        Args:
            config: Optional optimizer configuration
        """
        self.config = config or OptimizerConfig()
        self.lock = threading.Lock()
        self.stats = {
            "prompts_processed": 0,
            "total_original_tokens": 0,
            "total_optimized_tokens": 0,
            "total_tokens_saved": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # Token approximation (rough estimate: ~4 chars per token)
        self.chars_per_token = 4

        # Initialize template cache
        self.template_cache = TemplateCache()
        self.cache_enabled = (
            self.config.enable_template_caching and
            settings.cache_enabled
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using approximation.

        Note: This is a rough approximation. For accurate token counting,
        use tiktoken or the Anthropic API's token counting feature.

        Args:
            text: Text to count tokens in

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Approximate: ~4 characters per token for English text
        # This varies by language and content type
        return max(1, len(text) // self.chars_per_token)

    def optimize(self, prompt: str,
                preserve_code_blocks: Optional[bool] = None) -> Tuple[str, PromptStats]:
        """
        Optimize a prompt to reduce token usage.

        Checks the template cache first to reuse previously optimized prompts.
        If not found in cache, performs optimization and caches the result.

        Args:
            prompt: The prompt to optimize
            preserve_code_blocks: Whether to preserve code blocks

        Returns:
            Tuple of (optimized_prompt, stats)
        """
        with self.lock:
            # Check cache first if enabled
            if self.cache_enabled:
                cache_key = self.template_cache.generate_key(prompt, self.config)
                cached = self.template_cache.get(cache_key)

                if cached is not None:
                    # Cache hit - return cached optimization
                    self.stats["cache_hits"] += 1
                    self.stats["prompts_processed"] += 1

                    stats = PromptStats(
                        original_tokens=cached["original_tokens"],
                        optimized_tokens=cached["optimized_tokens"],
                        compression_ratio=cached["compression_ratio"],
                        optimizations_applied=cached["optimizations_applied"],
                    )

                    return cached["optimized"], stats
                else:
                    self.stats["cache_misses"] += 1

            # Cache miss or caching disabled - perform optimization
            original_tokens = self.count_tokens(prompt)
            optimizations = []
            optimized = prompt

            # Apply whitespace optimization
            if self.config.enable_whitespace_removal:
                optimized = self._optimize_whitespace(optimized)
                if len(optimized) < len(prompt):
                    optimizations.append("whitespace_normalization")

            # Apply duplicate removal
            if self.config.enable_duplicate_removal:
                optimized = self._remove_duplicates(optimized)
                if len(optimized) < len(prompt):
                    optimizations.append("duplicate_removal")

            # Apply template compression
            if self.config.enable_template_compression:
                optimized = self._compress_templates(optimized)
                if len(optimized) < len(prompt):
                    optimizations.append("template_compression")

            # Calculate stats
            optimized_tokens = self.count_tokens(optimized)
            tokens_saved = original_tokens - optimized_tokens
            compression_ratio = tokens_saved / original_tokens if original_tokens > 0 else 0

            stats = PromptStats(
                original_tokens=original_tokens,
                optimized_tokens=optimized_tokens,
                compression_ratio=compression_ratio,
                optimizations_applied=optimizations,
            )

            # Update global stats
            self.stats["prompts_processed"] += 1
            self.stats["total_original_tokens"] += original_tokens
            self.stats["total_optimized_tokens"] += optimized_tokens
            self.stats["total_tokens_saved"] += tokens_saved

            # Cache the result if enabled
            if self.cache_enabled:
                cache_key = self.template_cache.generate_key(prompt, self.config)
                # Use settings.cache_ttl for template cache TTL
                self.template_cache.set(
                    cache_key,
                    prompt,
                    optimized,
                    stats,
                    ttl=settings.cache_ttl
                )

            return optimized, stats

    def _optimize_whitespace(self, text: str) -> str:
        """
        Optimize whitespace by removing excessive blank lines and spaces.

        Preserves code blocks if preserve_code_blocks is enabled.

        Args:
            text: Text to optimize

        Returns:
            Optimized text
        """
        if not self.config.preserve_code_blocks:
            # Simple whitespace optimization
            # Replace multiple spaces with single space
            text = re.sub(r' +', ' ', text)
            # Replace multiple newlines with max 2 newlines
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n\n', text)
            return text.strip()

        # Preserve code blocks
        lines = text.split('\n')
        in_code_block = False
        optimized_lines = []
        consecutive_blank = 0

        for line in lines:
            # Check for code block markers
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                optimized_lines.append(line)
                consecutive_blank = 0
                continue

            if in_code_block:
                # Preserve exact whitespace in code blocks
                optimized_lines.append(line)
                consecutive_blank = 0
            else:
                # Optimize non-code text
                stripped = line.strip()
                if not stripped:
                    consecutive_blank += 1
                    if consecutive_blank <= 2:  # Allow max 2 blank lines
                        optimized_lines.append(line)
                else:
                    consecutive_blank = 0
                    # Remove trailing spaces
                    optimized_lines.append(line.rstrip())

        return '\n'.join(optimized_lines)

    def _remove_duplicates(self, text: str) -> str:
        """
        Remove duplicate consecutive lines.

        Args:
            text: Text to deduplicate

        Returns:
            Text with duplicates removed
        """
        lines = text.split('\n')
        seen = set()
        unique_lines = []

        for line in lines:
            # Use stripped version for comparison but preserve original
            line_key = line.strip()
            if line_key and line_key in seen and not line.startswith(' '):
                # Skip duplicate (but not indented lines which might be code)
                continue
            seen.add(line_key)
            unique_lines.append(line)

        return '\n'.join(unique_lines)

    def _compress_templates(self, text: str) -> str:
        """
        Compress common template patterns.

        Removes redundant boilerplate like repeated instructions.

        Args:
            text: Text to compress

        Returns:
            Compressed text
        """
        # Remove repeated phrases
        patterns = [
            (r'Please +', 'Please '),
            (r'Make sure to +', 'Ensure '),
            (r'You should +', ''),
            (r'You need to +', ''),
            (r'You must +', ''),
        ]

        compressed = text
        for pattern, replacement in patterns:
            compressed = re.sub(pattern, replacement, compressed)

        return compressed

    def truncate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Truncate a prompt to fit within max tokens.

        Attempts to truncate intelligently by preserving structure.

        Args:
            prompt: The prompt to truncate
            max_tokens: Maximum tokens (defaults to config.max_tokens)

        Returns:
            Truncated prompt
        """
        if max_tokens is None:
            max_tokens = self.config.max_tokens

        current_tokens = self.count_tokens(prompt)
        if current_tokens <= max_tokens:
            return prompt

        # Simple truncation: take first N characters
        # A smarter implementation would preserve sections
        max_chars = max_tokens * self.chars_per_token
        truncated = prompt[:max_chars]

        # Try to end at a newline
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.9:  # If newline is close to end
            truncated = truncated[:last_newline]

        return truncated

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics.

        Returns:
            Dictionary containing optimizer metrics
        """
        with self.lock:
            total_prompts = self.stats["prompts_processed"]
            total_original = self.stats["total_original_tokens"]
            total_optimized = self.stats["total_optimized_tokens"]

            avg_compression = 0
            if total_original > 0:
                avg_compression = (total_original - total_optimized) / total_original

            return {
                "prompts_processed": total_prompts,
                "total_original_tokens": total_original,
                "total_optimized_tokens": total_optimized,
                "total_tokens_saved": self.stats["total_tokens_saved"],
                "average_compression_ratio": avg_compression,
            }

    def reset_stats(self):
        """Reset optimizer statistics."""
        with self.lock:
            for key in self.stats:
                self.stats[key] = 0

    def batch_optimize(self, prompts: List[str]) -> List[Tuple[str, PromptStats]]:
        """
        Optimize multiple prompts.

        Args:
            prompts: List of prompts to optimize

        Returns:
            List of (optimized_prompt, stats) tuples
        """
        results = []
        for prompt in prompts:
            optimized, stats = self.optimize(prompt)
            results.append((optimized, stats))
        return results

    def clear_template_cache(self):
        """Clear all cached templates."""
        self.template_cache.clear()
        with self.lock:
            self.stats["cache_hits"] = 0
            self.stats["cache_misses"] = 0

    def get_template_cache_stats(self) -> Dict[str, Any]:
        """
        Get template cache statistics.

        Returns:
            Dictionary containing cache metrics
        """
        return self.template_cache.get_cache_stats()

    def get_cache_size(self) -> int:
        """
        Get the number of templates in the cache.

        Returns:
            Number of cached templates
        """
        return self.template_cache.get_size()

    def cleanup_expired_cache_entries(self) -> int:
        """
        Remove expired entries from the template cache.

        Returns:
            Number of entries removed
        """
        return self.template_cache.cleanup_expired()
