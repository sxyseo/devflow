#!/usr/bin/env python3
"""
DevFlow - Autonomous AI Development System

Main entry point for running the DevFlow autonomous development system.

Usage:
    python run.py [command] [options]

Commands:
    start                  Start the orchestrator
    run-project            Run a complete project from idea
    run-story              Run a single story
    status                 Show system status
    list-agents            List all agents
    list-tasks             List all tasks
    cleanup                Cleanup resources
    plugin-list            List installed plugins
    plugin-search          Search for plugins in the marketplace
    plugin-info            Get information about a specific plugin
    plugin-install         Install a plugin from the marketplace
    plugin-uninstall       Uninstall a plugin
    plugin-update          Update a plugin to the latest version
    plugin-marketplace-stats Show marketplace statistics
    help                   Show this help message

Examples:
    # Start the orchestrator
    python run.py start

    # Run a project
    python run.py run-project "A task management app for AI developers"

    # Run a story
    python run.py run-story my-project story-123

    # Check status
    python run.py status

    # List installed plugins
    python run.py plugin-list

    # Search for plugins
    python run.py plugin-search "agent"

    # Install a plugin
    python run.py plugin-install custom-agent

    # Get plugin info
    python run.py plugin-info custom-agent

    # Update a plugin
    python run.py plugin-update custom-agent

    # Uninstall a plugin
    python run.py plugin-uninstall custom-agent

    # Show marketplace stats
    python run.py plugin-marketplace-stats

    # Cleanup
    python run.py cleanup
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from devflow.core.orchestrator import get_orchestrator
from devflow.config.settings import settings
from devflow.marketplace import MarketplaceClient, PluginInstaller


def cmd_start(args):
    """Start the orchestrator."""
    orchestrator = get_orchestrator()
    orchestrator.start()

    print("\nOrchestrator is running. Press Ctrl+C to stop.")
    print("Use 'python run.py status' to check status in another terminal.\n")

    # Keep running
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.stop()


def cmd_run_project(args):
    """Run a complete project."""
    orchestrator = get_orchestrator()

    project_name = args.name if hasattr(args, 'name') and args.name else None
    project_id = orchestrator.run_project(args.idea, project_name)

    print(f"\n✓ Project '{project_id}' started successfully!")
    print(f"Use 'python run.py status' to monitor progress.\n")


def cmd_run_story(args):
    """Run a single story."""
    orchestrator = get_orchestrator()

    workflow_id = orchestrator.run_story(args.project, args.story)

    print(f"\n✓ Story '{args.story}' started successfully!")
    print(f"Workflow ID: {workflow_id}")
    print(f"Use 'python run.py status' to monitor progress.\n")


def cmd_status(args):
    """Show system status."""
    orchestrator = get_orchestrator()

    status = orchestrator.get_status()

    print("\n" + "=" * 60)
    print("📊 DevFlow System Status")
    print("=" * 60)

    # State metrics
    print("\n📈 System Metrics:")
    for key, value in status["state"].items():
        if isinstance(value, dict):
            print(f"  {key.capitalize()}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    # Agent metrics
    print(f"\n🤖 Agent Metrics:")
    for key, value in status["agents"].items():
        print(f"  {key}: {value}")

    # Scheduler metrics
    print(f"\n⏰ Scheduler Metrics:")
    for key, value in status["scheduler"].items():
        print(f"  {key}: {value}")

    # Sessions
    print(f"\n🖥️  Active Sessions: {status['sessions']['active']}")
    if status["sessions"]["list"]:
        print(f"  Sessions: {', '.join(status['sessions']['list'])}")

    print("=" * 60 + "\n")


def cmd_list_agents(args):
    """List all agents."""
    orchestrator = get_orchestrator()

    agents = orchestrator.list_agents()

    print("\n" + "=" * 60)
    print("🤖 Agents")
    print("=" * 60)

    if not agents:
        print("No agents found.")
    else:
        for agent in agents:
            print(f"\n  ID: {agent['id']}")
            print(f"  Type: {agent['type']}")
            print(f"  Status: {agent['status']}")
            print(f"  Tasks Completed: {agent.get('tasks_completed', 0)}")
            print(f"  Tasks Failed: {agent.get('tasks_failed', 0)}")

    print("=" * 60 + "\n")


def cmd_list_tasks(args):
    """List all tasks."""
    orchestrator = get_orchestrator()

    status_filter = args.status if hasattr(args, 'status') and args.status else None
    tasks = orchestrator.list_tasks(status_filter)

    print("\n" + "=" * 60)
    print(f"📝 Tasks{' - Filter: ' + status_filter if status_filter else ''}")
    print("=" * 60)

    if not tasks:
        print("No tasks found.")
    else:
        for task in tasks:
            print(f"\n  ID: {task['id'][:8]}...")
            print(f"  Type: {task['type']}")
            print(f"  Description: {task['description'][:60]}...")
            print(f"  Status: {task['status']}")
            print(f"  Priority: {task['priority']}")

    print("=" * 60 + "\n")


def cmd_cleanup(args):
    """Cleanup resources."""
    import sys

    response = input("\n⚠️  This will cleanup all DevFlow resources. Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cleanup cancelled.")
        return

    orchestrator = get_orchestrator()

    # Stop orchestrator
    orchestrator.stop()

    # Cleanup sessions
    orchestrator.sessions.cleanup_all_sessions()
    print("✓ All tmux sessions cleaned up")

    # Cleanup worktrees
    if settings.worktrees_dir.exists():
        import shutil
        try:
            shutil.rmtree(settings.worktrees_dir)
            print("✓ Worktrees cleaned up")
        except Exception as e:
            print(f"✗ Error cleaning worktrees: {e}")

    # Reset state
    orchestrator.state.reset()
    print("✓ State reset")

    print("\n✓ Cleanup complete!\n")


def cmd_plugin_list(args):
    """List installed plugins."""
    installer = PluginInstaller()
    plugins = installer.list_installed_plugins()

    print("\n" + "=" * 60)
    print("🔌 Installed Plugins")
    print("=" * 60)

    if not plugins:
        print("No plugins installed.")
    else:
        for plugin in plugins:
            print(f"\n  Name: {plugin.name}")
            print(f"  Version: {plugin.version}")
            print(f"  Source: {plugin.source}")
            print(f"  Path: {plugin.installed_path}")

    print("=" * 60 + "\n")


def cmd_plugin_search(args):
    """Search for plugins in the marketplace."""
    client = MarketplaceClient()
    plugins = client.search_plugins(args.query, plugin_type=args.type, limit=args.limit)

    print("\n" + "=" * 60)
    print(f"🔍 Plugin Search Results for '{args.query}'")
    print("=" * 60)

    if not plugins:
        print("No plugins found matching your search.")
    else:
        for plugin in plugins:
            status_icon = "✓" if plugin.installed else " "
            print(f"\n  {status_icon} {plugin.name} (v{plugin.version})")
            print(f"  Type: {plugin.plugin_type}")
            print(f"  Author: {plugin.author}")
            print(f"  Description: {plugin.description[:70]}...")
            if plugin.rating > 0:
                print(f"  Rating: {'★' * int(plugin.rating)}{'☆' * (5 - int(plugin.rating))} ({plugin.rating})")
            print(f"  Downloads: {plugin.downloads}")

    print("=" * 60 + "\n")


def cmd_plugin_info(args):
    """Get information about a specific plugin."""
    client = MarketplaceClient()
    plugin = client.get_plugin_info(args.name)

    if not plugin:
        print(f"\n❌ Plugin '{args.name}' not found in marketplace.\n")
        return

    print("\n" + "=" * 60)
    print(f"📦 Plugin: {plugin.name}")
    print("=" * 60)

    print(f"\n  Version: {plugin.version}")
    print(f"  Type: {plugin.plugin_type}")
    print(f"  Author: {plugin.author}")
    print(f"  Description: {plugin.description}")
    print(f"  License: {plugin.license}")

    if plugin.homepage:
        print(f"  Homepage: {plugin.homepage}")
    if plugin.repository:
        print(f"  Repository: {plugin.repository}")
    if plugin.documentation:
        print(f"  Documentation: {plugin.documentation}")

    if plugin.rating > 0:
        print(f"  Rating: {'★' * int(plugin.rating)}{'☆' * (5 - int(plugin.rating))} ({plugin.rating})")
    print(f"  Downloads: {plugin.downloads}")

    if plugin.keywords:
        print(f"  Keywords: {', '.join(plugin.keywords)}")

    if plugin.dependencies:
        print(f"  Dependencies: {', '.join(plugin.dependencies)}")

    if plugin.devflow_version:
        print(f"  Requires DevFlow: {plugin.devflow_version}")

    status = "Installed" if plugin.installed else "Not installed"
    if plugin.installed and plugin.installed_version:
        status += f" (v{plugin.installed_version})"
    print(f"  Status: {status}")

    print("=" * 60 + "\n")


def cmd_plugin_install(args):
    """Install a plugin from the marketplace."""
    installer = PluginInstaller()

    print(f"\n📦 Installing plugin '{args.name}'...")

    result = installer.install_plugin(args.name, source=args.source, version=args.version, force=args.force)

    if result.success:
        print(f"\n✓ Successfully installed {result.plugin_name} v{result.version}")
        if result.installed_path:
            print(f"  Location: {result.installed_path}")
        if result.dependencies_installed:
            print(f"  Dependencies installed: {', '.join(result.dependencies_installed)}")
        if result.warnings:
            print(f"  Warnings: {', '.join(result.warnings)}")
        print()
    else:
        print(f"\n✗ Failed to install plugin: {result.error}\n")


def cmd_plugin_uninstall(args):
    """Uninstall a plugin."""
    installer = PluginInstaller()

    print(f"\n🗑️  Uninstalling plugin '{args.name}'...")

    result = installer.uninstall_plugin(args.name, force=args.force)

    if result.success:
        print(f"\n✓ Successfully uninstalled {result.plugin_name}")
        if result.warnings:
            print(f"  Warnings: {', '.join(result.warnings)}")
        print()
    else:
        print(f"\n✗ Failed to uninstall plugin: {result.error}\n")


def cmd_plugin_update(args):
    """Update a plugin to the latest version."""
    installer = PluginInstaller()

    print(f"\n🔄 Updating plugin '{args.name}'...")

    result = installer.update_plugin(args.name)

    if result.success:
        print(f"\n✓ Successfully updated {result.plugin_name} to v{result.version}")
        if result.dependencies_installed:
            print(f"  Dependencies installed: {', '.join(result.dependencies_installed)}")
        if result.warnings:
            print(f"  Warnings: {', '.join(result.warnings)}")
        print()
    else:
        print(f"\n✗ Failed to update plugin: {result.error}\n")


def cmd_plugin_marketplace_stats(args):
    """Show marketplace statistics."""
    client = MarketplaceClient()

    stats = client.get_statistics()

    print("\n" + "=" * 60)
    print("📊 Marketplace Statistics")
    print("=" * 60)

    print(f"\n  Total Plugins: {stats['total_plugins']}")
    print(f"  Total Downloads: {stats['total_downloads']}")

    print(f"\n  Plugins by Type:")
    for plugin_type, count in stats['plugins_by_type'].items():
        print(f"    {plugin_type}: {count}")

    print(f"\n  Plugins by Source:")
    for source, count in stats['plugins_by_source'].items():
        print(f"    {source}: {count}")

    if stats['average_rating'] > 0:
        print(f"\n  Average Rating: {stats['average_rating']:.2f} / 5.0")

    # Cache info
    cache_info = client.get_cache_info()
    print(f"\n  Cache:")
    print(f"    Cached plugins: {cache_info['cached_plugins']}")
    print(f"    Active sources: {cache_info['sources']}")

    print("=" * 60 + "\n")


def cmd_help(args):
    """Show help message."""
    print(__doc__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DevFlow - Autonomous AI Development System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # start command
    subparsers.add_parser('start', help='Start the orchestrator')

    # run-project command
    run_project_parser = subparsers.add_parser('run-project', help='Run a complete project')
    run_project_parser.add_argument('idea', help='Project idea/description')
    run_project_parser.add_argument('--name', help='Project name (optional)')

    # run-story command
    run_story_parser = subparsers.add_parser('run-story', help='Run a single story')
    run_story_parser.add_argument('project', help='Project ID')
    run_story_parser.add_argument('story', help='Story ID')

    # status command
    subparsers.add_parser('status', help='Show system status')

    # list-agents command
    subparsers.add_parser('list-agents', help='List all agents')

    # list-tasks command
    list_tasks_parser = subparsers.add_parser('list-tasks', help='List all tasks')
    list_tasks_parser.add_argument('--status', help='Filter by status')

    # cleanup command
    subparsers.add_parser('cleanup', help='Cleanup resources')

    # plugin-list command
    subparsers.add_parser('plugin-list', help='List installed plugins')

    # plugin-search command
    plugin_search_parser = subparsers.add_parser('plugin-search', help='Search for plugins in the marketplace')
    plugin_search_parser.add_argument('query', help='Search query')
    plugin_search_parser.add_argument('--type', help='Filter by plugin type (agent, task_source, integration)')
    plugin_search_parser.add_argument('--limit', type=int, help='Maximum number of results')

    # plugin-info command
    plugin_info_parser = subparsers.add_parser('plugin-info', help='Get information about a specific plugin')
    plugin_info_parser.add_argument('name', help='Plugin name')

    # plugin-install command
    plugin_install_parser = subparsers.add_parser('plugin-install', help='Install a plugin from the marketplace')
    plugin_install_parser.add_argument('name', help='Plugin name')
    plugin_install_parser.add_argument('--source', help='Custom source URL/path')
    plugin_install_parser.add_argument('--version', help='Specific version to install')
    plugin_install_parser.add_argument('--force', action='store_true', help='Force reinstallation')

    # plugin-uninstall command
    plugin_uninstall_parser = subparsers.add_parser('plugin-uninstall', help='Uninstall a plugin')
    plugin_uninstall_parser.add_argument('name', help='Plugin name')
    plugin_uninstall_parser.add_argument('--force', action='store_true', help='Force uninstallation')

    # plugin-update command
    plugin_update_parser = subparsers.add_parser('plugin-update', help='Update a plugin to the latest version')
    plugin_update_parser.add_argument('name', help='Plugin name')

    # plugin-marketplace-stats command
    subparsers.add_parser('plugin-marketplace-stats', help='Show marketplace statistics')

    # help command
    subparsers.add_parser('help', help='Show help message')

    args = parser.parse_args()

    if not args.command or args.command == 'help':
        cmd_help(args)
        return

    # Dispatch command
    commands = {
        'start': cmd_start,
        'run-project': cmd_run_project,
        'run-story': cmd_run_story,
        'status': cmd_status,
        'list-agents': cmd_list_agents,
        'list-tasks': cmd_list_tasks,
        'cleanup': cmd_cleanup,
        'plugin-list': cmd_plugin_list,
        'plugin-search': cmd_plugin_search,
        'plugin-info': cmd_plugin_info,
        'plugin-install': cmd_plugin_install,
        'plugin-uninstall': cmd_plugin_uninstall,
        'plugin-update': cmd_plugin_update,
        'plugin-marketplace-stats': cmd_plugin_marketplace_stats,
        'help': cmd_help,
    }

    cmd_func = commands.get(args.command)

    if cmd_func:
        try:
            cmd_func(args)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        print("Use 'python run.py help' to see available commands")
        sys.exit(1)


if __name__ == '__main__':
    main()
