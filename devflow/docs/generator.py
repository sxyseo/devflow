"""
Documentation Generator - Generate documentation from analyzed code.

Creates and updates documentation files including API documentation,
README files, and architecture diagrams based on code analysis.
"""

import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DocumentationFormat(Enum):
    """Supported documentation output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    RST = "rst"
    JSON = "json"
    UNKNOWN = "unknown"


class DocumentationSection(Enum):
    """Types of documentation sections."""
    API_REFERENCE = "api_reference"
    GETTING_STARTED = "getting_started"
    ARCHITECTURE = "architecture"
    EXAMPLES = "examples"
    CHANGELOG = "changelog"
    CONTRIBUTING = "contributing"
    UNKNOWN = "unknown"


@dataclass
class DocumentationConfig:
    """Configuration for documentation generation."""
    output_format: DocumentationFormat = DocumentationFormat.MARKDOWN
    include_private: bool = False
    include_internal: bool = False
    add_toc: bool = True
    add_index: bool = True
    output_dir: str = "docs"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GeneratedDocumentation:
    """Generated documentation content and metadata."""
    content: str
    format: DocumentationFormat
    file_path: str
    sections: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.sections is None:
            self.sections = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ArchitectureDiagram:
    """Architecture diagram representation."""
    diagram_type: str  # mermaid, plantuml, etc.
    content: str
    file_path: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


class DocumentationGenerator:
    """
    Generates documentation from analyzed code.

    Features:
    - Generate API documentation in Markdown
    - Update README files with code information
    - Sync architecture diagrams with code structure
    - Support multiple output formats
    - Maintain table of contents and indices
    """

    def __init__(self, config: DocumentationConfig = None):
        """
        Initialize the documentation generator.

        Args:
            config: Optional configuration for documentation generation
        """
        self.config = config or DocumentationConfig()
        self._output_dir = Path(self.config.output_dir)

    def generate_api_docs(
        self,
        analyzed_code: Dict[str, Any],
        output_path: str = None
    ) -> GeneratedDocumentation:
        """
        Generate API documentation from analyzed code.

        Args:
            analyzed_code: Dictionary containing analyzed code information
            output_path: Optional output file path

        Returns:
            GeneratedDocumentation object with content and metadata

        Raises:
            ValueError: If analyzed_code is invalid
            IOError: If unable to write output file
        """
        if not analyzed_code:
            raise ValueError("analyzed_code cannot be empty")

        # This will be implemented in subtask-2-2
        # For now, return a placeholder
        content = self._generate_api_markdown(analyzed_code)

        if output_path:
            self._write_documentation(content, output_path)
        else:
            output_path = str(self._output_dir / "api.md")

        return GeneratedDocumentation(
            content=content,
            format=DocumentationFormat.MARKDOWN,
            file_path=output_path,
            sections=["API Reference"],
        )

    def update_readme(
        self,
        readme_path: str,
        changes: List[Any],
        analyzed_code: Dict[str, Any] = None
    ) -> bool:
        """
        Update README file with code changes and information.

        Args:
            readme_path: Path to the README file
            changes: List of code changes to document
            analyzed_code: Optional analyzed code information

        Returns:
            True if README was updated, False otherwise

        Raises:
            FileNotFoundError: If readme_path doesn't exist
            IOError: If unable to update README
        """
        readme = Path(readme_path)

        if not readme.exists():
            raise FileNotFoundError(f"README not found: {readme_path}")

        # This will be implemented in subtask-2-3
        # For now, return False indicating no update
        return False

    def sync_architecture_diagrams(
        self,
        code_structure: Dict[str, Any],
        diagram_dir: str = None
    ) -> List[ArchitectureDiagram]:
        """
        Synchronize architecture diagrams with code structure.

        Args:
            code_structure: Dictionary representing code structure
            diagram_dir: Optional directory for diagram files

        Returns:
            List of updated/created ArchitectureDiagram objects

        Raises:
            ValueError: If code_structure is invalid
            IOError: If unable to write diagram files
        """
        if not code_structure:
            raise ValueError("code_structure cannot be empty")

        # This will be implemented in subtask-2-4
        # For now, return empty list
        return []

    def generate_documentation(
        self,
        analyzed_code: Dict[str, Any],
        sections: List[DocumentationSection] = None
    ) -> GeneratedDocumentation:
        """
        Generate complete documentation with multiple sections.

        Args:
            analyzed_code: Dictionary containing analyzed code information
            sections: Optional list of sections to include

        Returns:
            GeneratedDocumentation object with complete documentation

        Raises:
            ValueError: If analyzed_code is invalid
        """
        if not analyzed_code:
            raise ValueError("analyzed_code cannot be empty")

        if sections is None:
            sections = [
                DocumentationSection.API_REFERENCE,
                DocumentationSection.GETTING_STARTED,
                DocumentationSection.ARCHITECTURE,
            ]

        content_parts = []

        # Add table of contents if configured
        if self.config.add_toc:
            content_parts.append(self._generate_toc(sections))

        # Generate each section
        for section in sections:
            section_content = self._generate_section(section, analyzed_code)
            content_parts.append(section_content)

        content = "\n\n".join(content_parts)

        return GeneratedDocumentation(
            content=content,
            format=self.config.output_format,
            file_path=str(self._output_dir / "docs.md"),
            sections=[s.value for s in sections],
        )

    def _generate_toc(
        self,
        sections: List[DocumentationSection]
    ) -> str:
        """
        Generate table of contents.

        Args:
            sections: List of documentation sections

        Returns:
            Markdown table of contents
        """
        toc_lines = ["## Table of Contents\n"]

        for section in sections:
            section_name = section.value.replace("_", " ").title()
            anchor = section.value.lower()
            toc_lines.append(f"- [{section_name}](#{anchor})")

        return "\n".join(toc_lines)

    def _generate_section(
        self,
        section: DocumentationSection,
        analyzed_code: Dict[str, Any]
    ) -> str:
        """
        Generate a specific documentation section.

        Args:
            section: The section to generate
            analyzed_code: Analyzed code information

        Returns:
            Generated section content
        """
        if section == DocumentationSection.API_REFERENCE:
            return self._generate_api_markdown(analyzed_code)
        elif section == DocumentationSection.GETTING_STARTED:
            return self._generate_getting_started(analyzed_code)
        elif section == DocumentationSection.ARCHITECTURE:
            return self._generate_architecture_section(analyzed_code)
        else:
            return f"## {section.value.replace('_', ' ').title()}\n\nContent pending..."

    def _generate_api_markdown(self, analyzed_code: Dict[str, Any]) -> str:
        """
        Generate API documentation in Markdown format.

        Args:
            analyzed_code: Dictionary containing analyzed code information

        Returns:
            Markdown formatted API documentation
        """
        # Placeholder implementation - will be expanded in subtask-2-2
        lines = ["# API Reference\n"]

        if "functions" in analyzed_code:
            lines.append("## Functions\n")
            for func in analyzed_code.get("functions", []):
                func_name = func.get("name", "unknown")
                lines.append(f"### {func_name}\n")

        if "classes" in analyzed_code:
            lines.append("## Classes\n")
            for cls in analyzed_code.get("classes", []):
                cls_name = cls.get("name", "unknown")
                lines.append(f"### {cls_name}\n")

        return "\n".join(lines)

    def _generate_getting_started(self, analyzed_code: Dict[str, Any]) -> str:
        """
        Generate getting started section.

        Args:
            analyzed_code: Analyzed code information

        Returns:
            Getting started content
        """
        return "## Getting Started\n\nInstallation and usage instructions pending..."

    def _generate_architecture_section(self, analyzed_code: Dict[str, Any]) -> str:
        """
        Generate architecture documentation section.

        Args:
            analyzed_code: Analyzed code information

        Returns:
            Architecture section content
        """
        return "## Architecture\n\nArchitecture overview pending..."

    def _write_documentation(self, content: str, output_path: str) -> None:
        """
        Write documentation content to file.

        Args:
            content: Documentation content to write
            output_path: Path to output file

        Raises:
            IOError: If unable to write file
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise IOError(f"Failed to write documentation to {output_path}: {e}")

    def _parse_template(self, template_path: str) -> str:
        """
        Parse a documentation template file.

        Args:
            template_path: Path to template file

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template = Path(template_path)

        if not template.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template, "r", encoding="utf-8") as f:
            return f.read()

    def _apply_template(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Apply variables to a template.

        Args:
            template: Template string with placeholders
            variables: Dictionary of variables to substitute

        Returns:
            Rendered template
        """
        result = template

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        return result
