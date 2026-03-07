"""
Orchestrator - Main coordinator for the DevFlow system.

Coordinates all agents, workflows, and system components.
"""

import asyncio
import signal
import sys
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import json

from .state_tracker import StateTracker, AgentStatus, TaskStatus
from .session_manager import SessionManager
from .agent_manager import AgentManager
from .task_scheduler import TaskScheduler, Task, TaskPriority
from ..docs.generator import DocumentationGenerator
from ..config.settings import settings


class Orchestrator:
    """
    Main orchestrator for the DevFlow autonomous development system.

    The Orchestrator coordinates:
    - Agent lifecycle management
    - Task scheduling and execution
    - Workflow orchestration
    - Session management
    - System state tracking

    It's the central hub that brings all components together.
    """

    def __init__(self):
        # Initialize settings
        settings.ensure_directories()
        settings.save()

        # Initialize core components
        self.state = StateTracker()
        self.sessions = SessionManager()
        self.agents = AgentManager(self.state, self.sessions)
        self.scheduler = TaskScheduler(self.state, self.agents)
        self.docs_generator = DocumentationGenerator()

        # Control flags
        self._running = False
        self._shutdown_event = threading.Event()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the orchestrator."""
        if self._running:
            print("Orchestrator is already running")
            return

        print("🚀 Starting DevFlow Orchestrator")
        print("=" * 60)

        self._running = True

        # Start session monitoring
        self.sessions.start_monitoring()
        print("✓ Session monitoring started")

        # Start task scheduler
        self.scheduler.start()
        print("✓ Task scheduler started")

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()

        print("✓ Orchestrator started successfully")
        print("=" * 60)
        print()

    def stop(self):
        """Stop the orchestrator."""
        if not self._running:
            return

        print("\n🛑 Stopping DevFlow Orchestrator")
        print("=" * 60)

        self._running = False
        self._shutdown_event.set()

        # Stop scheduler
        self.scheduler.stop()
        print("✓ Task scheduler stopped")

        # Stop session monitoring
        self.sessions.stop_monitoring()
        print("✓ Session monitoring stopped")

        # Cleanup agents
        self.agents.cleanup_all_agents()
        print("✓ All agents cleaned up")

        # Save final state
        self.state.save()
        print("✓ State saved")

        print("=" * 60)
        print("Orchestrator stopped")

    def run_project(self, project_idea: str, project_name: str = None) -> str:
        """
        Run a complete project from idea to implementation.

        This is the main entry point for autonomous development.

        Args:
            project_idea: Description of the project
            project_name: Optional project name

        Returns:
            Project ID
        """
        if not self._running:
            self.start()

        # Generate project ID
        project_id = project_name or f"project-{int(time.time())}"

        print(f"\n🎯 Starting Project: {project_id}")
        print(f"Idea: {project_idea}")
        print("=" * 60)

        # Create project directory
        project_dir = settings.workspace_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        # Run BMAD planning workflow
        task_ids = self._run_planning_workflow(project_id, project_idea)

        print(f"\n✓ Planning phase initiated with {len(task_ids)} tasks")
        print(f"Project ID: {project_id}")
        print(f"Project directory: {project_dir}")

        return project_id

    def _run_planning_workflow(self, project_id: str, project_idea: str) -> List[str]:
        """
        Run the BMAD planning workflow.

        Creates and schedules all planning tasks:
        1. Product Owner - Product brief
        2. Business Analyst - PRD
        3. Architect - Architecture
        4. UX Designer - UX specifications
        5. Scrum Master - Stories breakdown
        6. Readiness Check - GO/NO-GO decision
        7. Documentation Generator - Comprehensive documentation
        """
        task_ids = []

        # Task 1: Product Owner
        task_id = self.scheduler.create_task(
            task_type="planning",
            description=f"Generate product brief for: {project_idea}",
            agent_type="product-owner",
            priority=TaskPriority.HIGH.value,
            input_data={
                "project_id": project_id,
                "project_idea": project_idea,
                "output_path": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/product-brief.md",
            }
        )
        task_ids.append(task_id)

        # Task 2: Business Analyst (depends on Product Owner)
        task_id = self.scheduler.create_task(
            task_type="planning",
            description="Create PRD with user journeys",
            agent_type="business-analyst",
            priority=TaskPriority.HIGH.value,
            dependencies=[task_ids[0]],
            input_data={
                "project_id": project_id,
                "input_brief": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/product-brief.md",
                "output_path": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/prd.md",
            }
        )
        task_ids.append(task_id)

        # Task 3: Architect (depends on Business Analyst)
        task_id = self.scheduler.create_task(
            task_type="planning",
            description="Design system architecture",
            agent_type="architect",
            priority=TaskPriority.HIGH.value,
            dependencies=[task_ids[1]],
            input_data={
                "project_id": project_id,
                "input_prd": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/prd.md",
                "output_path": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/architecture.md",
            }
        )
        task_ids.append(task_id)

        # Task 4: UX Designer (depends on Business Analyst)
        task_id = self.scheduler.create_task(
            task_type="planning",
            description="Create UX specifications",
            agent_type="ux-designer",
            priority=TaskPriority.HIGH.value,
            dependencies=[task_ids[1]],
            input_data={
                "project_id": project_id,
                "input_prd": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/prd.md",
                "output_path": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/ux-spec.md",
            }
        )
        task_ids.append(task_id)

        # Task 5: Scrum Master (depends on PRD, Architecture, UX)
        task_id = self.scheduler.create_task(
            task_type="planning",
            description="Break down into epics and stories",
            agent_type="scrum-master",
            priority=TaskPriority.HIGH.value,
            dependencies=[task_ids[1], task_ids[2], task_ids[3]],
            input_data={
                "project_id": project_id,
                "input_prd": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/prd.md",
                "output_stories": f"{settings.workspace_dir}/{project_id}/.taskmaster/stories/",
            }
        )
        task_ids.append(task_id)

        # Task 6: Readiness Check (depends on all previous)
        task_id = self.scheduler.create_task(
            task_type="planning",
            description="Perform readiness check and GO/NO-GO decision",
            agent_type="readiness-check",
            priority=TaskPriority.CRITICAL.value,
            dependencies=[task_ids[4]],
            input_data={
                "project_id": project_id,
                "docs_dir": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/",
                "stories_dir": f"{settings.workspace_dir}/{project_id}/.taskmaster/stories/",
                "output_path": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/readiness-check.md",
            }
        )
        task_ids.append(task_id)

        # Task 7: Documentation Generation (depends on Readiness Check)
        task_id = self.scheduler.create_task(
            task_type="documentation",
            description="Generate comprehensive project documentation",
            agent_type="documentation-generator",
            priority=TaskPriority.MEDIUM.value,
            dependencies=[task_ids[5]],
            input_data={
                "project_id": project_id,
                "docs_dir": f"{settings.workspace_dir}/{project_id}/.taskmaster/docs/",
                "stories_dir": f"{settings.workspace_dir}/{project_id}/.taskmaster/stories/",
                "output_dir": f"{settings.workspace_dir}/{project_id}/docs/",
            }
        )
        task_ids.append(task_id)

        return task_ids

    def run_story(self, project_id: str, story_id: str) -> str:
        """
        Run a single story through the development workflow.

        Args:
            project_id: Project identifier
            story_id: Story identifier

        Returns:
            Workflow ID
        """
        workflow_id = f"workflow-{project_id}-{story_id}-{int(time.time())}"

        print(f"\n📋 Starting Story: {story_id}")
        print(f"Project: {project_id}")
        print("=" * 60)

        # Create development workflow tasks
        task_ids = []

        # Task 1: Create Story
        task_id = self.scheduler.create_task(
            task_type="development",
            description=f"Create story file for {story_id}",
            agent_type="create-story",
            priority=TaskPriority.HIGH.value,
            input_data={
                "project_id": project_id,
                "story_id": story_id,
            }
        )
        task_ids.append(task_id)

        # Task 2: Dev Story (implementation)
        task_id = self.scheduler.create_task(
            task_type="development",
            description=f"Implement story {story_id} with TDD",
            agent_type="dev-story",
            priority=TaskPriority.HIGH.value,
            dependencies=[task_ids[0]],
            input_data={
                "project_id": project_id,
                "story_id": story_id,
            }
        )
        task_ids.append(task_id)

        # Task 3: Code Review
        task_id = self.scheduler.create_task(
            task_type="quality",
            description=f"Review implementation of {story_id}",
            agent_type="code-review",
            priority=TaskPriority.HIGH.value,
            dependencies=[task_ids[1]],
            input_data={
                "project_id": project_id,
                "story_id": story_id,
            }
        )
        task_ids.append(task_id)

        # Task 4: UX Review
        task_id = self.scheduler.create_task(
            task_type="quality",
            description=f"Review UX compliance for {story_id}",
            agent_type="ux-review",
            priority=TaskPriority.MEDIUM.value,
            dependencies=[task_ids[1]],
            input_data={
                "project_id": project_id,
                "story_id": story_id,
            }
        )
        task_ids.append(task_id)

        # Task 5: QA Testing
        task_id = self.scheduler.create_task(
            task_type="quality",
            description=f"Execute tests for {story_id}",
            agent_type="qa-tester",
            priority=TaskPriority.CRITICAL.value,
            dependencies=[task_ids[1]],
            input_data={
                "project_id": project_id,
                "story_id": story_id,
            }
        )
        task_ids.append(task_id)

        # Task 6: Retrospective
        task_id = self.scheduler.create_task(
            task_type="quality",
            description=f"Capture learnings for {story_id}",
            agent_type="retrospective",
            priority=TaskPriority.LOW.value,
            dependencies=[task_ids[2], task_ids[3], task_ids[4]],
            input_data={
                "project_id": project_id,
                "story_id": story_id,
            }
        )
        task_ids.append(task_id)

        return workflow_id

    def run_documentation_generation(
        self,
        project_id: str,
        input_paths: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Generate documentation for a project.

        Creates comprehensive documentation including API reference,
        architecture documentation, and getting started guides.

        Args:
            project_id: Project identifier
            input_paths: Optional dictionary with paths to documentation sources
                        (docs_dir, stories_dir, source_dir)

        Returns:
            Dictionary with generation results including output paths
        """
        project_dir = settings.workspace_dir / project_id

        # Default paths if not provided
        if input_paths is None:
            input_paths = {
                "docs_dir": str(project_dir / ".taskmaster" / "docs"),
                "stories_dir": str(project_dir / ".taskmaster" / "stories"),
                "source_dir": str(project_dir / "src"),
            }

        output_dir = project_dir / "docs"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📚 Generating Documentation for: {project_id}")
        print("=" * 60)

        try:
            # Import here to avoid circular dependencies
            from ..docs.analyzer import CodeAnalyzer
            from ..docs.generator import DocumentationSection

            # Analyze the project structure
            analyzer = CodeAnalyzer()
            source_dir = Path(input_paths.get("source_dir", str(project_dir / "src")))

            if source_dir.exists():
                print(f"Analyzing source code in: {source_dir}")
                analyzed_code = analyzer.analyze_project(str(source_dir))
            else:
                print(f"Source directory not found, generating docs from planning artifacts")
                analyzed_code = {"modules": [], "classes": [], "functions": []}

            # Generate documentation sections
            sections = [
                DocumentationSection.GETTING_STARTED,
                DocumentationSection.ARCHITECTURE,
            ]

            # Add API reference if we have code
            if analyzed_code.get("modules") or analyzed_code.get("classes"):
                sections.append(DocumentationSection.API_REFERENCE)

            # Generate documentation
            print(f"Generating documentation sections: {[s.value for s in sections]}")
            result = self.docs_generator.generate_documentation(
                analyzed_code=analyzed_code,
                sections=sections
            )

            # Write documentation
            output_path = output_dir / "docs.md"
            with open(output_path, "w") as f:
                f.write(result.content)

            print(f"✓ Documentation generated successfully")
            print(f"  Output: {output_path}")
            print(f"  Sections: {', '.join(result.sections)}")
            print("=" * 60)

            return {
                "project_id": project_id,
                "output_path": str(output_path),
                "sections": result.sections,
                "format": result.format.value,
                "status": "success",
            }

        except Exception as e:
            print(f"✗ Documentation generation failed: {e}")
            return {
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
            }

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Print system status every 30 seconds
                self._print_status()

                # Wait for shutdown event or timeout
                self._shutdown_event.wait(timeout=30)

            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)

    def _print_status(self):
        """Print current system status."""
        metrics = self.state.get_metrics()
        agent_metrics = self.agents.get_agent_metrics()
        scheduler_metrics = self.scheduler.get_metrics()

        print("\n" + "=" * 60)
        print("📊 DevFlow System Status")
        print("=" * 60)

        # Tasks
        print(f"\n📝 Tasks:")
        print(f"  Total: {metrics['tasks']['total']}")
        print(f"  Completed: {metrics['tasks']['completed']}")
        print(f"  Failed: {metrics['tasks']['failed']}")
        print(f"  Pending: {metrics['tasks']['pending']}")
        print(f"  Success Rate: {metrics['tasks']['success_rate']:.1%}")

        # Agents
        print(f"\n🤖 Agents:")
        print(f"  Total: {agent_metrics['total_agents']}")
        print(f"  Idle: {agent_metrics['idle']}")
        print(f"  Running: {agent_metrics['running']}")
        print(f"  Tasks Completed: {agent_metrics['total_tasks_completed']}")

        # Scheduler
        print(f"\n⏰ Scheduler:")
        print(f"  Queue Size: {scheduler_metrics['queue_size']}")
        print(f"  In Progress: {scheduler_metrics['in_progress']}")

        print("=" * 60)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "state": self.state.get_metrics(),
            "agents": self.agents.get_agent_metrics(),
            "scheduler": self.scheduler.get_metrics(),
            "sessions": {
                "active": len(self.sessions.get_active_sessions()),
                "list": self.sessions.list_sessions(),
            }
        }

    def create_task(self, **kwargs) -> str:
        """Create a new task."""
        return self.scheduler.create_task(**kwargs)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        return list(self.state.get_all_agents().values())

    def list_tasks(self, status: str = None) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by status."""
        all_tasks = self.state.get_all_tasks()

        if status:
            return [t for t in all_tasks.values() if t["status"] == status]

        return list(all_tasks.values())


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get the singleton orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = Orchestrator()

    return _orchestrator
