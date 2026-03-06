"""
Skill Registry - Register and manage available skills.

Provides a centralized registry for all available skills.
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional

from .skill_parser import SkillParser, ParsedSkill


class SkillRegistry:
    """
    Registry for managing available skills.

    Provides:
    - Skill discovery and registration
    - Skill lookup by name or type
    - Skill dependency resolution
    """

    def __init__(self, skills_dir: Path = None):
        self.skills_dir = skills_dir or Path(__file__).parent.parent / "skills"
        self.parser = SkillParser(self.skills_dir)
        self._skills: Dict[str, ParsedSkill] = {}
        self._skills_by_type: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

        # Auto-discover skills
        self.discover_skills()

    def discover_skills(self):
        """Discover and register all skills in the skills directory."""
        skill_files = self.parser.list_skills()

        for skill_file in skill_files:
            try:
                skill = self.parser.parse_file(skill_file)
                self.register_skill(skill)
            except Exception as e:
                print(f"Warning: Failed to parse skill {skill_file}: {e}")

    def register_skill(self, skill: ParsedSkill):
        """Register a skill."""
        with self._lock:
            skill_name = skill.metadata.name.lower().replace(' ', '-')

            self._skills[skill_name] = skill

            # Index by type
            skill_type = skill_file_to_type(skill.source_file)
            if skill_type not in self._skills_by_type:
                self._skills_by_type[skill_type] = []

            if skill_name not in self._skills_by_type[skill_type]:
                self._skills_by_type[skill_type].append(skill_name)

    def get_skill(self, skill_name: str) -> Optional[ParsedSkill]:
        """Get a skill by name."""
        # Try exact match
        if skill_name in self._skills:
            return self._skills[skill_name]

        # Try fuzzy match
        skill_key = skill_name.lower().replace(' ', '-')
        if skill_key in self._skills:
            return self._skills[skill_key]

        # Try partial match
        for key, skill in self._skills.items():
            if skill_name.lower() in key.lower():
                return skill

        return None

    def get_skills_by_type(self, skill_type: str) -> List[ParsedSkill]:
        """Get all skills of a specific type."""
        skill_names = self._skills_by_type.get(skill_type, [])

        return [
            self._skills[name]
            for name in skill_names
            if name in self._skills
        ]

    def list_skill_names(self) -> List[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def list_skill_types(self) -> List[str]:
        """List all skill types."""
        return list(self._skills_by_type.keys())

    def get_skill_dependencies(self, skill_name: str) -> List[str]:
        """Get dependencies for a skill."""
        skill = self.get_skill(skill_name)

        if not skill:
            return []

        return skill.metadata.related_skills

    def resolve_dependencies(self, skill_name: str, resolved: List[str] = None) -> List[str]:
        """Recursively resolve all dependencies for a skill."""
        if resolved is None:
            resolved = []

        skill = self.get_skill(skill_name)

        if not skill:
            return resolved

        for dep in skill.metadata.related_skills:
            if dep not in resolved:
                resolved.append(dep)
                self.resolve_dependencies(dep, resolved)

        return resolved


def skill_file_to_type(skill_file: Path) -> str:
    """Extract skill type from file path."""
    # Skills are organized in directories like: skills/{type}/{skill-name}.md
    parts = skill_file.parts

    # Find the skills directory and get the next part
    try:
        skills_index = parts.index("skills")
        if skills_index + 1 < len(parts):
            return parts[skills_index + 1]
    except ValueError:
        pass

    # Fallback: use parent directory name
    return skill_file.parent.name
