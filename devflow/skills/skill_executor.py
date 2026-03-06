"""
Skill Executor - Execute skills with AI agents.

Handles the execution of skills by AI agents with proper context and validation.
"""

import subprocess
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from .skill_parser import ParsedSkill, SkillParameter
from .skill_registry import SkillRegistry
from ..core.session_manager import SessionManager
from ..core.state_tracker import StateTracker
from ..config.settings import settings


@dataclass
class SkillExecutionContext:
    """Context for skill execution."""
    skill_name: str
    parameters: Dict[str, Any]
    agent_id: str
    project_id: str = None
    working_dir: Path = None
    timeout: int = 3600
    session_name: str = None


@dataclass
class SkillExecutionResult:
    """Result of skill execution."""
    success: bool
    skill_name: str
    agent_id: str
    output: Any = None
    error: str = None
    halted: bool = False
    halt_reason: str = None
    execution_time: float = 0
    artifacts: Dict[str, Any] = None


class SkillExecutor:
    """
    Executes skills using AI agents.

    Features:
    - Skill execution with proper context
    - HALT condition detection and handling
    - Result validation
    - Artifact capture
    """

    def __init__(self, registry: SkillRegistry, session_manager: SessionManager,
                 state_tracker: StateTracker):
        self.registry = registry
        self.sessions = session_manager
        self.state = state_tracker
        self._executions: Dict[str, SkillExecutionResult] = {}
        self._lock = threading.Lock()

    def execute(self, context: SkillExecutionContext) -> SkillExecutionResult:
        """
        Execute a skill with the given context.

        Args:
            context: Skill execution context

        Returns:
            SkillExecutionResult
        """
        # Get skill definition
        skill = self.registry.get_skill(context.skill_name)

        if not skill:
            return SkillExecutionResult(
                success=False,
                skill_name=context.skill_name,
                agent_id=context.agent_id,
                error=f"Skill '{context.skill_name}' not found"
            )

        start_time = time.time()

        try:
            # Validate parameters
            self._validate_parameters(skill, context.parameters)

            # Create tmux session for execution
            session = self.sessions.create_session(
                agent_id=context.agent_id,
                agent_type=self._get_agent_type(skill),
                task=self._build_task_prompt(skill, context),
            )

            context.session_name = session.name

            # Monitor execution
            result = self._monitor_execution(context, skill)

            # Record execution time
            result.execution_time = time.time() - start_time

            # Store result
            with self._lock:
                self._executions[f"{context.skill_name}-{context.agent_id}"] = result

            return result

        except Exception as e:
            return SkillExecutionResult(
                success=False,
                skill_name=context.skill_name,
                agent_id=context.agent_id,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def _validate_parameters(self, skill: ParsedSkill, parameters: Dict[str, Any]):
        """Validate required parameters."""
        required_params = [p for p in skill.metadata.inputs if p.required]

        for param in required_params:
            if param.name not in parameters:
                raise ValueError(f"Missing required parameter: {param.name}")

    def _get_agent_type(self, skill: ParsedSkill) -> str:
        """Determine agent type from skill."""
        # Extract agent type from skill source file path
        if skill.source_file:
            parts = skill.source_file.parts
            try:
                skills_index = parts.index("skills")
                if skills_index + 1 < len(parts):
                    return parts[skills_index + 1]
            except ValueError:
                pass

        # Fallback: guess from skill name
        skill_name = skill.metadata.name.lower()

        if "planning" in skill_name or "owner" in skill_name or "analyst" in skill_name:
            return "planning"
        elif "dev" in skill_name or "story" in skill_name:
            return "development"
        elif "review" in skill_name or "qa" in skill_name or "test" in skill_name:
            return "quality"
        else:
            return "general"

    def _build_task_prompt(self, skill: ParsedSkill, context: SkillExecutionContext) -> str:
        """Build the task prompt for the agent."""
        prompt = f"""# Task: Execute {skill.metadata.name}

## Purpose
{skill.metadata.purpose}

## Parameters
"""

        for param_name, param_value in context.parameters.items():
            prompt += f"- {param_name}: {param_value}\n"

        prompt += f"""
## Process Steps
"""

        for i, step in enumerate(skill.metadata.process, 1):
            prompt += f"{i}. {step}\n"

        prompt += f"""
## Quality Checklist
"""

        for item in skill.metadata.quality_checklist:
            prompt += f"- [ ] {item}\n"

        prompt += f"""
## HALT Conditions
"""

        for condition in skill.metadata.halt_conditions:
            prompt += f"- **{condition['reason']}**: `HALT: {condition['reason']} | Context: {condition['context']}`\n"

        prompt += f"""
## Expected Outputs
"""

        for output in skill.metadata.outputs:
            prompt += f"- {output}\n"

        prompt += """
---
Please execute this task following the process steps. Ensure all quality checklist items are met. If you encounter a HALT condition, return the appropriate HALT message with context.
"""

        return prompt

    def _monitor_execution(self, context: SkillExecutionContext,
                          skill: ParsedSkill) -> SkillExecutionResult:
        """Monitor skill execution and detect HALT conditions."""
        start_time = time.time()
        check_interval = 10  # Check every 10 seconds

        while time.time() - start_time < context.timeout:
            time.sleep(check_interval)

            # Check if session is still running
            if not self.sessions.session_exists(context.session_name):
                # Session ended, check for output
                output = self.sessions.get_session_output(context.session_name)

                # Check for HALT conditions
                halt_info = self._check_halt_conditions(output, skill)

                if halt_info:
                    return SkillExecutionResult(
                        success=False,
                        skill_name=context.skill_name,
                        agent_id=context.agent_id,
                        halted=True,
                        halt_reason=halt_info,
                        output=output,
                        execution_time=time.time() - start_time
                    )

                # Success
                return SkillExecutionResult(
                    success=True,
                    skill_name=context.skill_name,
                    agent_id=context.agent_id,
                    output=output,
                    execution_time=time.time() - start_time,
                    artifacts=self._extract_artifacts(output, skill)
                )

        # Timeout
        return SkillExecutionResult(
            success=False,
            skill_name=context.skill_name,
            agent_id=context.agent_id,
            error=f"Execution timeout after {context.timeout}s",
            execution_time=context.timeout
        )

    def _check_halt_conditions(self, output: str, skill: ParsedSkill) -> Optional[str]:
        """Check if output contains HALT conditions."""
        for condition in skill.metadata.halt_conditions:
            if condition['reason'].lower() in output.lower():
                return condition['reason']

        # General HALT detection
        if 'HALT:' in output.upper():
            # Extract HALT message
            import re
            match = re.search(r'HALT:\s*([^|\n]+)', output, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_artifacts(self, output: str, skill: ParsedSkill) -> Dict[str, Any]:
        """Extract artifacts from output."""
        artifacts = {}

        # Look for file paths in output
        import re
        file_paths = re.findall(r'`?([a-zA-Z0-9_/-]+\.[a-z]+)`?', output)

        for file_path in file_paths:
            path = Path(file_path)
            if path.exists() and path.is_file():
                artifacts[path.name] = {
                    "path": str(path),
                    "size": path.stat().st_size,
                    "type": path.suffix[1:] if path.suffix else "unknown"
                }

        return artifacts

    def get_execution_result(self, skill_name: str, agent_id: str) -> Optional[SkillExecutionResult]:
        """Get a previous execution result."""
        key = f"{skill_name}-{agent_id}"

        with self._lock:
            return self._executions.get(key)

    def list_executions(self) -> List[Dict[str, Any]]:
        """List all executions."""
        with self._lock:
            return [
                {
                    "skill_name": result.skill_name,
                    "agent_id": result.agent_id,
                    "success": result.success,
                    "halted": result.halted,
                    "execution_time": result.execution_time,
                }
                for result in self._executions.values()
            ]
