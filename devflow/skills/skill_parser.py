"""
Skill Parser - Parse skill definitions from markdown files.

Extracts skill metadata, parameters, and execution instructions from markdown files.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class SkillParameter:
    """A parameter definition for a skill."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class SkillMetadata:
    """Metadata extracted from a skill definition."""
    name: str
    purpose: str
    when_to_use: List[str]
    inputs: List[SkillParameter]
    outputs: List[str]
    process: List[str]
    quality_checklist: List[str]
    halt_conditions: List[Dict[str, str]]
    example_usage: str
    related_skills: List[str]
    next_steps: List[str]


@dataclass
class ParsedSkill:
    """A parsed skill ready for execution."""
    metadata: SkillMetadata
    source_file: Path
    raw_content: str
    sections: Dict[str, str] = field(default_factory=dict)


class SkillParser:
    """
    Parses skill definitions from markdown files.

    Skills are defined in markdown format with structured sections.
    """

    def __init__(self, skills_dir: Path = None):
        self.skills_dir = skills_dir or Path(__file__).parent.parent / "skills"

    def parse_file(self, file_path: Path) -> ParsedSkill:
        """
        Parse a skill definition from a markdown file.

        Args:
            file_path: Path to the skill markdown file

        Returns:
            ParsedSkill object
        """
        raw_content = file_path.read_text()
        return self.parse_content(raw_content, file_path)

    def parse_content(self, content: str, source_file: Path = None) -> ParsedSkill:
        """
        Parse skill definition from markdown content.

        Args:
            content: Markdown content
            source_file: Optional source file path

        Returns:
            ParsedSkill object
        """
        sections = self._extract_sections(content)

        metadata = SkillMetadata(
            name=self._extract_name(sections, content),
            purpose=self._extract_purpose(sections),
            when_to_use=self._extract_when_to_use(sections),
            inputs=self._extract_inputs(sections),
            outputs=self._extract_outputs(sections),
            process=self._extract_process(sections),
            quality_checklist=self._extract_quality_checklist(sections),
            halt_conditions=self._extract_halt_conditions(sections),
            example_usage=self._extract_example_usage(sections),
            related_skills=self._extract_related_skills(sections),
            next_steps=self._extract_next_steps(sections),
        )

        return ParsedSkill(
            metadata=metadata,
            source_file=source_file or Path("<unknown>"),
            raw_content=content,
            sections=sections,
        )

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract markdown sections by header."""
        sections = {}

        # Split by headers
        lines = content.split('\n')
        current_section = "intro"
        current_content = []

        for line in lines:
            if line.startswith('##'):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()

                # Start new section
                current_section = line[2:].strip().lower().replace(' ', '-')
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _extract_name(self, sections: Dict[str, str], content: str) -> str:
        """Extract skill name from content."""
        # First line is usually the name
        first_line = content.split('\n')[0]
        return first_line.replace('#', '').strip()

    def _extract_purpose(self, sections: Dict[str, str]) -> str:
        """Extract purpose section."""
        purpose_key = None
        for key in sections.keys():
            if 'purpose' in key:
                purpose_key = key
                break

        return sections.get(purpose_key, "No purpose defined")

    def _extract_when_to_use(self, sections: Dict[str, str]) -> List[str]:
        """Extract when to use section as list."""
        when_key = None
        for key in sections.keys():
            if 'when' in key and 'use' in key:
                when_key = key
                break

        content = sections.get(when_key, "")
        return [line.strip().lstrip('-*').strip() for line in content.split('\n') if line.strip().lstrip('-*')]

    def _extract_inputs(self, sections: Dict[str, str]) -> List[SkillParameter]:
        """Extract input parameters."""
        inputs_key = None
        for key in sections.keys():
            if 'input' in key:
                inputs_key = key
                break

        content = sections.get(inputs_key, "")
        parameters = []

        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('-') and ':' in line:
                # Parse parameter: "- name: description"
                parts = line[1:].split(':', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    description = parts[1].strip()
                    parameters.append(SkillParameter(
                        name=name,
                        type="string",
                        description=description,
                        required=True
                    ))

        return parameters

    def _extract_outputs(self, sections: Dict[str, str]) -> List[str]:
        """Extract outputs section as list."""
        outputs_key = None
        for key in sections.keys():
            if 'output' in key:
                outputs_key = key
                break

        content = sections.get(outputs_key, "")
        return [line.strip().lstrip('-*').strip() for line in content.split('\n') if line.strip().lstrip('-*')]

    def _extract_process(self, sections: Dict[str, str]) -> List[str]:
        """Extract process steps."""
        process_key = None
        for key in sections.keys():
            if 'process' in key:
                process_key = key
                break

        content = sections.get(process_key, "")
        return [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]

    def _extract_quality_checklist(self, sections: Dict[str, str]) -> List[str]:
        """Extract quality checklist."""
        quality_key = None
        for key in sections.keys():
            if 'quality' in key or 'checklist' in key:
                quality_key = key
                break

        content = sections.get(quality_key, "")
        return [line.strip().lstrip('-*').strip() for line in content.split('\n') if line.strip().lstrip('-*')]

    def _extract_halt_conditions(self, sections: Dict[str, str]) -> List[Dict[str, str]]:
        """Extract HALT conditions."""
        halt_key = None
        for key in sections.keys():
            if 'halt' in key.lower():
                halt_key = key
                break

        content = sections.get(halt_key, "")
        conditions = []

        for line in content.split('\n'):
            line = line.strip()
            if 'HALT' in line and ':' in line:
                # Parse: "- **condition**: `HALT: reason | Context: context`"
                match = re.search(r'HALT:\s*([^|]+)\s*\|\s*Context:\s*(.+)', line)
                if match:
                    conditions.append({
                        "reason": match.group(1).strip(),
                        "context": match.group(2).strip()
                    })

        return conditions

    def _extract_example_usage(self, sections: Dict[str, str]) -> str:
        """Extract example usage section."""
        example_key = None
        for key in sections.keys():
            if 'example' in key:
                example_key = key
                break

        return sections.get(example_key, "")

    def _extract_related_skills(self, sections: Dict[str, str]) -> List[str]:
        """Extract related skills."""
        related_key = None
        for key in sections.keys():
            if 'related' in key:
                related_key = key
                break

        content = sections.get(related_key, "")
        return [line.strip().lstrip('-*').strip() for line in content.split('\n') if line.strip().lstrip('-*')]

    def _extract_next_steps(self, sections: Dict[str, str]) -> List[str]:
        """Extract next steps."""
        next_key = None
        for key in sections.keys():
            if 'next' in key or 'step' in key:
                next_key = key
                break

        content = sections.get(next_key, "")
        return [line.strip().lstrip('-*').strip() for line in content.split('\n') if line.strip().lstrip('-*')]

    def list_skills(self) -> List[Path]:
        """List all available skill files."""
        if not self.skills_dir.exists():
            return []

        return list(self.skills_dir.rglob("*.md"))

    def get_skill_path(self, skill_name: str) -> Optional[Path]:
        """Get the path to a skill by name."""
        skills = self.list_skills()

        for skill_file in skills:
            if skill_name.lower() in skill_file.name.lower():
                return skill_file

        return None
