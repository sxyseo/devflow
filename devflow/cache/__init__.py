"""
Cache System - Intelligent caching for API responses and prompts.

Provides efficient caching, prompt optimization, and batch processing
to reduce API usage and costs.
"""

from .base import CacheBackend, CacheEntry

__all__ = [
    'CacheBackend',
    'CacheEntry',
]
