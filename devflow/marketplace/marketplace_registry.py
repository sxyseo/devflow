"""
Marketplace Registry - Register and manage marketplace plugin metadata.

Provides a centralized registry for all available plugins from marketplace sources.
"""

import threading
from typing import Dict, List, Optional, Any

from .marketplace_client import MarketplacePluginInfo


class MarketplaceRegistry:
    """
    Registry for managing marketplace plugin metadata.

    Provides:
    - Plugin metadata registration and storage
    - Plugin lookup by name or type
    - Plugin search and filtering
    - Thread-safe plugin management
    """

    def __init__(self):
        self._plugins: Dict[str, MarketplacePluginInfo] = {}
        self._plugins_by_type: Dict[str, List[str]] = {}
        self._plugins_by_author: Dict[str, List[str]] = {}
        self._plugins_by_keyword: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def register_plugin(self, plugin_info: MarketplacePluginInfo) -> None:
        """
        Register a plugin from the marketplace.

        Args:
            plugin_info: MarketplacePluginInfo instance to register
        """
        with self._lock:
            plugin_name = plugin_info.name.lower().replace(' ', '-')

            self._plugins[plugin_name] = plugin_info

            # Index by type
            plugin_type = plugin_info.plugin_type
            if plugin_type not in self._plugins_by_type:
                self._plugins_by_type[plugin_type] = []

            if plugin_name not in self._plugins_by_type[plugin_type]:
                self._plugins_by_type[plugin_type].append(plugin_name)

            # Index by author
            author = plugin_info.author.lower()
            if author not in self._plugins_by_author:
                self._plugins_by_author[author] = []

            if plugin_name not in self._plugins_by_author[author]:
                self._plugins_by_author[author].append(plugin_name)

            # Index by keywords
            for keyword in plugin_info.keywords:
                keyword_key = keyword.lower()
                if keyword_key not in self._plugins_by_keyword:
                    self._plugins_by_keyword[keyword_key] = []

                if plugin_name not in self._plugins_by_keyword[keyword_key]:
                    self._plugins_by_keyword[keyword_key].append(plugin_name)

    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_name: Name of the plugin to unregister

        Returns:
            True if plugin was unregistered, False if not found
        """
        with self._lock:
            # Normalize plugin name
            plugin_name = plugin_name.lower().replace(' ', '-')

            if plugin_name not in self._plugins:
                return False

            # Get plugin info before removing
            plugin_info = self._plugins[plugin_name]

            # Remove from type index
            plugin_type = plugin_info.plugin_type
            if plugin_type in self._plugins_by_type:
                self._plugins_by_type[plugin_type] = [
                    name for name in self._plugins_by_type[plugin_type]
                    if name != plugin_name
                ]

                # Remove empty type lists
                if not self._plugins_by_type[plugin_type]:
                    del self._plugins_by_type[plugin_type]

            # Remove from author index
            author = plugin_info.author.lower()
            if author in self._plugins_by_author:
                self._plugins_by_author[author] = [
                    name for name in self._plugins_by_author[author]
                    if name != plugin_name
                ]

                # Remove empty author lists
                if not self._plugins_by_author[author]:
                    del self._plugins_by_author[author]

            # Remove from keyword index
            for keyword in plugin_info.keywords:
                keyword_key = keyword.lower()
                if keyword_key in self._plugins_by_keyword:
                    self._plugins_by_keyword[keyword_key] = [
                        name for name in self._plugins_by_keyword[keyword_key]
                        if name != plugin_name
                    ]

                    # Remove empty keyword lists
                    if not self._plugins_by_keyword[keyword_key]:
                        del self._plugins_by_keyword[keyword_key]

            # Remove plugin
            del self._plugins[plugin_name]

            return True

    def get_plugin(self, plugin_name: str) -> Optional[MarketplacePluginInfo]:
        """
        Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            MarketplacePluginInfo or None if not found
        """
        # Try exact match
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]

        # Try fuzzy match
        plugin_key = plugin_name.lower().replace(' ', '-')
        if plugin_key in self._plugins:
            return self._plugins[plugin_key]

        # Try partial match
        for key, plugin in self._plugins.items():
            if plugin_name.lower() in key.lower():
                return plugin

        return None

    def get_plugins_by_type(self, plugin_type: str) -> List[MarketplacePluginInfo]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugin to get (e.g., "agent", "task_source")

        Returns:
            List of MarketplacePluginInfo of the specified type
        """
        plugin_names = self._plugins_by_type.get(plugin_type, [])

        return [
            self._plugins[name]
            for name in plugin_names
            if name in self._plugins
        ]

    def get_plugins_by_author(self, author: str) -> List[MarketplacePluginInfo]:
        """
        Get all plugins by a specific author.

        Args:
            author: Author name to filter by

        Returns:
            List of MarketplacePluginInfo by the specified author
        """
        author_key = author.lower()
        plugin_names = self._plugins_by_author.get(author_key, [])

        return [
            self._plugins[name]
            for name in plugin_names
            if name in self._plugins
        ]

    def get_plugins_by_keyword(self, keyword: str) -> List[MarketplacePluginInfo]:
        """
        Get all plugins matching a keyword.

        Args:
            keyword: Keyword to search for

        Returns:
            List of MarketplacePluginInfo matching the keyword
        """
        keyword_key = keyword.lower()
        plugin_names = self._plugins_by_keyword.get(keyword_key, [])

        return [
            self._plugins[name]
            for name in plugin_names
            if name in self._plugins
        ]

    def search_plugins(self, query: str,
                      plugin_type: str = None,
                      author: str = None) -> List[MarketplacePluginInfo]:
        """
        Search for plugins matching a query.

        Args:
            query: Search query string
            plugin_type: Optional filter by plugin type
            author: Optional filter by author

        Returns:
            List of matching MarketplacePluginInfo
        """
        all_plugins = list(self._plugins.values())
        query_lower = query.lower()

        matching_plugins = []

        for plugin in all_plugins:
            # Type filter
            if plugin_type and plugin.plugin_type != plugin_type:
                continue

            # Author filter
            if author and plugin.author.lower() != author.lower():
                continue

            # Search in name, description, keywords
            search_fields = [
                plugin.name,
                plugin.description,
                " ".join(plugin.keywords),
            ]

            if any(query_lower in field.lower() for field in search_fields):
                matching_plugins.append(plugin)

        # Sort by relevance (name matches first, then by rating)
        matching_plugins.sort(
            key=lambda p: (
                query_lower in p.name.lower(),
                p.rating,
                -p.downloads,
            ),
            reverse=True
        )

        return matching_plugins

    def list_plugin_names(self) -> List[str]:
        """
        List all registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def list_plugin_types(self) -> List[str]:
        """
        List all plugin types.

        Returns:
            List of plugin types
        """
        return list(self._plugins_by_type.keys())

    def list_authors(self) -> List[str]:
        """
        List all authors.

        Returns:
            List of author names
        """
        return list(self._plugins_by_author.keys())

    def list_keywords(self) -> List[str]:
        """
        List all keywords.

        Returns:
            List of keywords
        """
        return list(self._plugins_by_keyword.keys())

    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """
        Get dependencies for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            List of plugin dependencies
        """
        plugin_info = self.get_plugin(plugin_name)

        if not plugin_info:
            return []

        return plugin_info.dependencies

    def get_popular_plugins(self, limit: int = 10) -> List[MarketplacePluginInfo]:
        """
        Get popular plugins (by downloads).

        Args:
            limit: Maximum number of plugins to return

        Returns:
            List of popular MarketplacePluginInfo
        """
        all_plugins = list(self._plugins.values())

        sorted_plugins = sorted(
            all_plugins,
            key=lambda p: p.downloads,
            reverse=True
        )

        return sorted_plugins[:limit]

    def get_top_rated_plugins(self, limit: int = 10,
                             min_rating: float = 4.0) -> List[MarketplacePluginInfo]:
        """
        Get top-rated plugins.

        Args:
            limit: Maximum number of plugins to return
            min_rating: Minimum rating required

        Returns:
            List of top-rated MarketplacePluginInfo
        """
        all_plugins = list(self._plugins.values())

        # Filter by minimum rating
        qualified_plugins = [
            p for p in all_plugins
            if p.rating >= min_rating
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

        Note: This is a placeholder that returns plugins with low download counts.
        In a real implementation, this would use plugin addition timestamps.

        Args:
            limit: Maximum number of plugins to return

        Returns:
            List of recently added MarketplacePluginInfo
        """
        all_plugins = list(self._plugins.values())

        # Sort by downloads (ascending) as a proxy for "new"
        sorted_plugins = sorted(
            all_plugins,
            key=lambda p: p.downloads,
        )

        return sorted_plugins[:limit]

    def filter_plugins(self,
                      plugin_type: str = None,
                      author: str = None,
                      min_rating: float = None,
                      min_downloads: int = None,
                      keywords: List[str] = None) -> List[MarketplacePluginInfo]:
        """
        Filter plugins by multiple criteria.

        Args:
            plugin_type: Optional filter by plugin type
            author: Optional filter by author
            min_rating: Optional minimum rating
            min_downloads: Optional minimum downloads
            keywords: Optional list of keywords to match

        Returns:
            List of filtered MarketplacePluginInfo
        """
        all_plugins = list(self._plugins.values())

        filtered_plugins = []

        for plugin in all_plugins:
            # Type filter
            if plugin_type and plugin.plugin_type != plugin_type:
                continue

            # Author filter
            if author and plugin.author.lower() != author.lower():
                continue

            # Rating filter
            if min_rating and plugin.rating < min_rating:
                continue

            # Downloads filter
            if min_downloads and plugin.downloads < min_downloads:
                continue

            # Keywords filter (must match at least one)
            if keywords:
                plugin_keywords_lower = [k.lower() for k in plugin.keywords]
                if not any(kw.lower() in plugin_keywords_lower for kw in keywords):
                    continue

            filtered_plugins.append(plugin)

        return filtered_plugins

    def get_plugin_count(self) -> int:
        """
        Get the total number of registered plugins.

        Returns:
            Number of registered plugins
        """
        return len(self._plugins)

    def get_plugin_count_by_type(self, plugin_type: str) -> int:
        """
        Get the number of plugins of a specific type.

        Args:
            plugin_type: Type of plugin to count

        Returns:
            Number of plugins of the specified type
        """
        return len(self._plugins_by_type.get(plugin_type, []))

    def get_plugin_count_by_author(self, author: str) -> int:
        """
        Get the number of plugins by a specific author.

        Args:
            author: Author name to count

        Returns:
            Number of plugins by the specified author
        """
        author_key = author.lower()
        return len(self._plugins_by_author.get(author_key, []))

    def is_plugin_registered(self, plugin_name: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is registered, False otherwise
        """
        return self.get_plugin(plugin_name) is not None

    def clear(self) -> None:
        """Clear all registered plugins."""
        with self._lock:
            self._plugins.clear()
            self._plugins_by_type.clear()
            self._plugins_by_author.clear()
            self._plugins_by_keyword.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        all_plugins = list(self._plugins.values())

        # Count by type
        type_counts = {}
        for plugin in all_plugins:
            type_counts[plugin.plugin_type] = type_counts.get(plugin.plugin_type, 0) + 1

        # Count by author
        author_counts = {}
        for plugin in all_plugins:
            author_counts[plugin.author] = author_counts.get(plugin.author, 0) + 1

        return {
            "total_plugins": len(all_plugins),
            "plugins_by_type": type_counts,
            "plugins_by_author": author_counts,
            "total_authors": len(self._plugins_by_author),
            "total_keywords": len(self._plugins_by_keyword),
            "total_downloads": sum(p.downloads for p in all_plugins),
            "average_rating": sum(p.rating for p in all_plugins if p.rating > 0) / max(1, len([p for p in all_plugins if p.rating > 0])),
        }
