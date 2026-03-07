"""
Marketplace Client - Plugin discovery and marketplace integration.

Provides interface for discovering, browsing, and querying plugins
from various marketplace sources (local registry, remote API, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
import urllib.request
import urllib.error

from ..config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MarketplacePluginInfo:
    """
    Information about a plugin available in the marketplace.

    Attributes:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        plugin_type: Type of plugin (agent, task_source, integration)
        source: Source URL or location
        homepage: Homepage URL
        repository: Repository URL
        documentation: Documentation URL
        license: Plugin license
        keywords: List of keywords for search
        downloads: Download count
        rating: Average rating (0-5)
        devflow_version: Required DevFlow version
        dependencies: List of plugin dependencies
        installed: Whether plugin is currently installed
        installed_version: Installed version (if any)
    """
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    source: str
    homepage: Optional[str] = None
    repository: Optional[str] = None
    documentation: Optional[str] = None
    license: str = "MIT"
    keywords: List[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    devflow_version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    installed: bool = False
    installed_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type,
            "source": self.source,
            "homepage": self.homepage,
            "repository": self.repository,
            "documentation": self.documentation,
            "license": self.license,
            "keywords": self.keywords,
            "downloads": self.downloads,
            "rating": self.rating,
            "devflow_version": self.devflow_version,
            "dependencies": self.dependencies,
            "installed": self.installed,
            "installed_version": self.installed_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketplacePluginInfo":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class MarketplaceSource:
    """
    Configuration for a marketplace source.

    Attributes:
        name: Source name
        type: Source type (local, remote, git)
        url: Source URL or path
        enabled: Whether source is enabled
        priority: Source priority (higher checked first)
    """
    name: str
    type: str
    url: str
    enabled: bool = True
    priority: int = 0


class MarketplaceClient:
    """
    Client for interacting with plugin marketplaces.

    The MarketplaceClient provides:
    - Plugin discovery and search
    - Plugin metadata retrieval
    - Multi-source support (local registry, remote APIs)
    - Installation source resolution
    """

    def __init__(self, sources: List[MarketplaceSource] = None,
                 cache_dir: Path = None):
        """
        Initialize the marketplace client.

        Args:
            sources: Optional list of marketplace sources
            cache_dir: Optional cache directory for downloaded metadata
        """
        self.sources = sources or self._default_sources()
        self.cache_dir = cache_dir or (settings.state_dir / "marketplace" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Plugin cache
        self._plugins_cache: Dict[str, List[MarketplacePluginInfo]] = {}
        self._cache_timestamp: float = 0

    def _default_sources(self) -> List[MarketplaceSource]:
        """
        Get default marketplace sources.

        Returns:
            List of default marketplace sources
        """
        # Local registry file (included with DevFlow)
        local_registry = Path(__file__).parent / "registry.json"

        sources = [
            MarketplaceSource(
                name="local",
                type="local",
                url=str(local_registry),
                enabled=True,
                priority=100,
            ),
            MarketplaceSource(
                name="devflow-official",
                type="remote",
                url="https://plugins.devflow.ai/registry.json",
                enabled=True,
                priority=50,
            ),
        ]

        return sources

    def discover_plugins(self, force_refresh: bool = False) -> List[MarketplacePluginInfo]:
        """
        Discover all available plugins from all enabled sources.

        Args:
            force_refresh: Force refresh of cached plugin data

        Returns:
            List of all discovered plugins
        """
        # Check cache
        if not force_refresh and self._plugins_cache:
            logger.info("Using cached plugin data")
            return list(self._plugins_cache.values())

        all_plugins = []

        # Query each source in priority order
        sorted_sources = sorted(
            [s for s in self.sources if s.enabled],
            key=lambda s: s.priority,
            reverse=True
        )

        for source in sorted_sources:
            try:
                logger.info(f"Querying marketplace source: {source.name}")
                plugins = self._query_source(source)

                # Merge plugins (later sources can add/update plugins)
                for plugin in plugins:
                    existing = next(
                        (p for p in all_plugins if p.name == plugin.name),
                        None
                    )

                    if existing:
                        # Update existing plugin with newer data
                        all_plugins.remove(existing)
                        all_plugins.append(plugin)
                    else:
                        all_plugins.append(plugin)

            except Exception as e:
                logger.error(f"Error querying source '{source.name}': {e}")

        # Update cache
        self._plugins_cache = {p.name: p for p in all_plugins}
        self._cache_timestamp = 0  # TODO: Use actual timestamp

        logger.info(f"Discovered {len(all_plugins)} plugins from {len(sorted_sources)} sources")
        return all_plugins

    def _query_source(self, source: MarketplaceSource) -> List[MarketplacePluginInfo]:
        """
        Query a single marketplace source.

        Args:
            source: Marketplace source to query

        Returns:
            List of plugins from the source

        Raises:
            Exception: If source query fails
        """
        if source.type == "local":
            return self._query_local_source(source)
        elif source.type == "remote":
            return self._query_remote_source(source)
        elif source.type == "git":
            return self._query_git_source(source)
        else:
            raise ValueError(f"Unknown source type: {source.type}")

    def _query_local_source(self, source: MarketplaceSource) -> List[MarketplacePluginInfo]:
        """
        Query a local marketplace source (file).

        Args:
            source: Local marketplace source

        Returns:
            List of plugins from the local registry

        Raises:
            Exception: If local file cannot be read
        """
        import time

        registry_path = Path(source.url)

        if not registry_path.exists():
            logger.warning(f"Local registry not found: {registry_path}")
            return []

        try:
            with open(registry_path, 'r') as f:
                data = json.load(f)

            plugins = []
            for plugin_data in data.get("plugins", []):
                try:
                    plugin = MarketplacePluginInfo.from_dict(plugin_data)
                    plugins.append(plugin)
                except Exception as e:
                    logger.warning(f"Error parsing plugin data: {e}")

            logger.info(f"Loaded {len(plugins)} plugins from local registry")
            return plugins

        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in local registry: {e}")
        except Exception as e:
            raise Exception(f"Error reading local registry: {e}")

    def _query_remote_source(self, source: MarketplaceSource) -> List[MarketplacePluginInfo]:
        """
        Query a remote marketplace source (HTTP/HTTPS).

        Args:
            source: Remote marketplace source

        Returns:
            List of plugins from the remote registry

        Raises:
            Exception: If remote source cannot be fetched
        """
        try:
            # Fetch remote registry
            req = urllib.request.Request(
                source.url,
                headers={
                    "User-Agent": "DevFlow-Marketplace-Client/1.0"
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            plugins = []
            for plugin_data in data.get("plugins", []):
                try:
                    plugin = MarketplacePluginInfo.from_dict(plugin_data)
                    plugins.append(plugin)
                except Exception as e:
                    logger.warning(f"Error parsing plugin data: {e}")

            logger.info(f"Loaded {len(plugins)} plugins from remote registry")
            return plugins

        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP error fetching remote registry: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error fetching remote registry: {e.reason}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in remote registry: {e}")
        except Exception as e:
            raise Exception(f"Error fetching remote registry: {e}")

    def _query_git_source(self, source: MarketplaceSource) -> List[MarketplacePluginInfo]:
        """
        Query a git-based marketplace source.

        Args:
            source: Git marketplace source

        Returns:
            List of plugins from the git repository

        Raises:
            Exception: If git repository cannot be cloned/fetched
        """
        # TODO: Implement git source support
        logger.warning(f"Git source support not yet implemented: {source.name}")
        return []

    def search_plugins(self, query: str,
                      plugin_type: str = None,
                      limit: int = None) -> List[MarketplacePluginInfo]:
        """
        Search for plugins matching a query.

        Args:
            query: Search query string
            plugin_type: Optional filter by plugin type
            limit: Optional maximum number of results

        Returns:
            List of matching plugins
        """
        all_plugins = self.discover_plugins()

        query_lower = query.lower()

        # Filter plugins
        matching_plugins = []

        for plugin in all_plugins:
            # Type filter
            if plugin_type and plugin.plugin_type != plugin_type:
                continue

            # Search in name, description, author, keywords
            search_fields = [
                plugin.name,
                plugin.description,
                plugin.author,
                " ".join(plugin.keywords),
            ]

            if any(query_lower in field.lower() for field in search_fields):
                matching_plugins.append(plugin)

        # Sort by relevance (simple scoring: name matches first)
        matching_plugins.sort(
            key=lambda p: (
                query_lower in p.name.lower(),  # Name matches first
                p.rating,  # Then by rating
                -p.downloads,  # Then by downloads
            ),
            reverse=True
        )

        if limit:
            matching_plugins = matching_plugins[:limit]

        return matching_plugins

    def get_plugin_info(self, plugin_name: str) -> Optional[MarketplacePluginInfo]:
        """
        Get information about a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            MarketplacePluginInfo or None if not found
        """
        all_plugins = self.discover_plugins()

        for plugin in all_plugins:
            if plugin.name == plugin_name:
                return plugin

        return None

    def get_plugins_by_type(self, plugin_type: str) -> List[MarketplacePluginInfo]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugin (agent, task_source, integration)

        Returns:
            List of plugins of the specified type
        """
        all_plugins = self.discover_plugins()

        return [
            plugin for plugin in all_plugins
            if plugin.plugin_type == plugin_type
        ]

    def get_popular_plugins(self, limit: int = 10) -> List[MarketplacePluginInfo]:
        """
        Get popular plugins (by downloads).

        Args:
            limit: Maximum number of plugins to return

        Returns:
            List of popular plugins
        """
        all_plugins = self.discover_plugins()

        sorted_plugins = sorted(
            all_plugins,
            key=lambda p: p.downloads,
            reverse=True
        )

        return sorted_plugins[:limit]

    def get_top_rated_plugins(self, limit: int = 10,
                             min_ratings: int = 5) -> List[MarketplacePluginInfo]:
        """
        Get top-rated plugins.

        Args:
            limit: Maximum number of plugins to return
            min_ratings: Minimum number of downloads/ratings required

        Returns:
            List of top-rated plugins
        """
        all_plugins = self.discover_plugins()

        # Filter by minimum downloads
        qualified_plugins = [
            p for p in all_plugins
            if p.downloads >= min_ratings
        ]

        # Sort by rating
        sorted_plugins = sorted(
            qualified_plugins,
            key=lambda p: p.rating,
            reverse=True
        )

        return sorted_plugins[:limit]

    def get_new_plugins(self, limit: int = 10) -> List[MarketplacePluginInfo]:
        """
        Get recently added plugins.

        Note: This is a placeholder. In a real implementation, this would
        use plugin creation/addition timestamps from the marketplace.

        Args:
            limit: Maximum number of plugins to return

        Returns:
            List of recently added plugins
        """
        # TODO: Implement proper new plugins detection
        # For now, return plugins with low download counts (assumed to be newer)
        all_plugins = self.discover_plugins()

        sorted_plugins = sorted(
            all_plugins,
            key=lambda p: p.downloads,
        )

        return sorted_plugins[:limit]

    def get_sources(self) -> List[MarketplaceSource]:
        """
        Get all marketplace sources.

        Returns:
            List of marketplace sources
        """
        return self.sources.copy()

    def add_source(self, source: MarketplaceSource) -> None:
        """
        Add a new marketplace source.

        Args:
            source: Marketplace source to add
        """
        self.sources.append(source)
        # Clear cache to force refresh
        self._plugins_cache.clear()

    def remove_source(self, source_name: str) -> bool:
        """
        Remove a marketplace source.

        Args:
            source_name: Name of the source to remove

        Returns:
            True if source was removed, False if not found
        """
        for i, source in enumerate(self.sources):
            if source.name == source_name:
                self.sources.pop(i)
                # Clear cache to force refresh
                self._plugins_cache.clear()
                return True

        return False

    def enable_source(self, source_name: str) -> bool:
        """
        Enable a marketplace source.

        Args:
            source_name: Name of the source to enable

        Returns:
            True if source was enabled, False if not found
        """
        for source in self.sources:
            if source.name == source_name:
                source.enabled = True
                # Clear cache to force refresh
                self._plugins_cache.clear()
                return True

        return False

    def disable_source(self, source_name: str) -> bool:
        """
        Disable a marketplace source.

        Args:
            source_name: Name of the source to disable

        Returns:
            True if source was disabled, False if not found
        """
        for source in self.sources:
            if source.name == source_name:
                source.enabled = False
                # Clear cache to force refresh
                self._plugins_cache.clear()
                return True

        return False

    def refresh_cache(self) -> None:
        """Force refresh of plugin cache."""
        self._plugins_cache.clear()
        self.discover_plugins(force_refresh=True)

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin cache.

        Returns:
            Dictionary with cache information
        """
        return {
            "cached_plugins": len(self._plugins_cache),
            "sources": len([s for s in self.sources if s.enabled]),
            "cache_dir": str(self.cache_dir),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get marketplace statistics.

        Returns:
            Dictionary with marketplace statistics
        """
        all_plugins = self.discover_plugins()

        # Count by type
        type_counts = {}
        for plugin in all_plugins:
            type_counts[plugin.plugin_type] = type_counts.get(plugin.plugin_type, 0) + 1

        # Count by source (if available)
        source_counts = {}
        for plugin in all_plugins:
            # Extract source from URL
            source_name = "unknown"
            if "github.com" in plugin.source:
                source_name = "github"
            elif "gitlab.com" in plugin.source:
                source_name = "gitlab"
            elif "devflow.ai" in plugin.source:
                source_name = "devflow-official"

            source_counts[source_name] = source_counts.get(source_name, 0) + 1

        return {
            "total_plugins": len(all_plugins),
            "plugins_by_type": type_counts,
            "plugins_by_source": source_counts,
            "total_downloads": sum(p.downloads for p in all_plugins),
            "average_rating": sum(p.rating for p in all_plugins if p.rating > 0) / max(1, len([p for p in all_plugins if p.rating > 0])),
        }
