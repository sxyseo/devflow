#!/usr/bin/env python3
"""
DevFlow - Autonomous AI Development System

Main entry point for running the DevFlow autonomous development system.

Usage:
    python run.py [command] [options]

Commands:
    start           Start the orchestrator
    run-project     Run a complete project from idea
    run-story       Run a single story
    status          Show system status
    list-agents     List all agents
    list-tasks      List all tasks
    cleanup         Cleanup resources
    help            Show this help message

Examples:
    # Start the orchestrator
    python run.py start

    # Run a project
    python run.py run-project "A task management app for AI developers"

    # Run a story
    python run.py run-story my-project story-123

    # Check status
    python run.py status

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
