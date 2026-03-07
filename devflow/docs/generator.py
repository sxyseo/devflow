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
        lines = ["# API Reference\n"]

        # Check if this is a single file analysis or multiple files
        if "file_path" in analyzed_code:
            # Single file analysis
            self._generate_single_file_docs(analyzed_code, lines)
        elif "files" in analyzed_code:
            # Multiple files analysis
            self._generate_multiple_files_docs(analyzed_code, lines)
        else:
            # Legacy format with top-level functions/classes
            self._generate_legacy_format_docs(analyzed_code, lines)

        return "\n".join(lines)

    def _generate_single_file_docs(
        self,
        file_analysis: Dict[str, Any],
        lines: List[str]
    ) -> None:
        """
        Generate documentation for a single analyzed file.

        Args:
            file_analysis: Analysis result for a single file
            lines: List to append documentation lines to
        """
        file_path = file_analysis.get("file_path", "unknown")
        lines.append(f"\n## File: {file_path}\n")

        # Add module docstring if present
        module_docstring = file_analysis.get("module_docstring")
        if module_docstring:
            lines.append(f"{module_docstring}\n")

        # Generate documentation for classes
        classes = file_analysis.get("classes", [])
        if classes:
            lines.append("\n### Classes\n")
            for cls in classes:
                self._generate_class_docs(cls, lines)

        # Generate documentation for functions
        functions = file_analysis.get("functions", [])
        if functions:
            lines.append("\n### Functions\n")
            for func in functions:
                self._generate_function_docs(func, lines)

    def _generate_multiple_files_docs(
        self,
        analyzed_code: Dict[str, Any],
        lines: List[str]
    ) -> None:
        """
        Generate documentation for multiple analyzed files.

        Args:
            analyzed_code: Analysis result containing multiple files
            lines: List to append documentation lines to
        """
        for file_data in analyzed_code.get("files", []):
            self._generate_single_file_docs(file_data, lines)

    def _generate_legacy_format_docs(
        self,
        analyzed_code: Dict[str, Any],
        lines: List[str]
    ) -> None:
        """
        Generate documentation from legacy format (top-level functions/classes).

        Args:
            analyzed_code: Analysis result in legacy format
            lines: List to append documentation lines to
        """
        # Generate documentation for classes
        classes = analyzed_code.get("classes", [])
        if classes:
            lines.append("\n## Classes\n")
            for cls in classes:
                self._generate_class_docs(cls, lines)

        # Generate documentation for functions
        functions = analyzed_code.get("functions", [])
        if functions:
            lines.append("\n## Functions\n")
            for func in functions:
                self._generate_function_docs(func, lines)

        # Generate documentation for API endpoints if present
        api_endpoints = analyzed_code.get("api_endpoints", [])
        if api_endpoints:
            lines.append("\n## API Endpoints\n")
            for endpoint in api_endpoints:
                self._generate_endpoint_docs(endpoint, lines)

    def _generate_class_docs(self, cls: Dict[str, Any], lines: List[str]) -> None:
        """
        Generate documentation for a class.

        Args:
            cls: Class information dictionary
            lines: List to append documentation lines to
        """
        class_name = cls.get("name", "Unknown")
        lines.append(f"\n#### Class: `{class_name}`\n")

        # Add class docstring
        docstring = cls.get("docstring")
        if docstring:
            lines.append(f"{docstring}\n")

        # Add class signature if available
        signature = cls.get("signature")
        if signature:
            lines.append(f"\n**Signature:** `{signature}`\n")

        # Add decorators if present
        decorators = cls.get("decorators", [])
        if decorators:
            lines.append("\n**Decorators:**\n")
            for decorator in decorators:
                lines.append(f"- `{decorator}`\n")
            lines.append("")

        # Add methods
        methods = cls.get("methods", [])
        if methods:
            lines.append("\n**Methods:**\n")
            for method in methods:
                method_name = method.get("name", "unknown")
                lines.append(f"\n##### `{class_name}.{method_name}`\n")

                # Add method docstring
                method_docstring = method.get("docstring")
                if method_docstring:
                    lines.append(f"{method_docstring}\n")

                # Add method signature
                method_signature = method.get("signature")
                if method_signature:
                    lines.append(f"\n**Signature:** `{method_signature}`\n")

                # Add parameters
                parameters = method.get("parameters", [])
                if parameters:
                    lines.append("\n**Parameters:**\n")
                    for param in parameters:
                        param_name = param.get("name", "unknown")
                        param_type = param.get("type", "")
                        param_desc = param.get("description", "")
                        default = param.get("default")

                        param_line = f"- `{param_name}`"
                        if param_type:
                            param_line += f" ({param_type})"
                        if default is not None:
                            param_line += f" = {default}"

                        lines.append(param_line)

                        if param_desc:
                            lines.append(f"  - {param_desc}")

                    lines.append("")

                # Add return type
                return_type = method.get("return_type")
                if return_type:
                    lines.append(f"\n**Returns:** `{return_type}`\n")

    def _generate_function_docs(
        self,
        func: Dict[str, Any],
        lines: List[str]
    ) -> None:
        """
        Generate documentation for a function.

        Args:
            func: Function information dictionary
            lines: List to append documentation lines to
        """
        func_name = func.get("name", "unknown")
        is_private = func_name.startswith("_")

        # Skip private functions if not configured to include them
        if is_private and not self.config.include_private:
            return

        lines.append(f"\n#### Function: `{func_name}`\n")

        # Add function docstring
        docstring = func.get("docstring")
        if docstring:
            lines.append(f"{docstring}\n")

        # Add function signature
        signature = func.get("signature")
        if signature:
            lines.append(f"\n**Signature:** `{signature}`\n")

        # Add decorators if present
        decorators = func.get("decorators", [])
        if decorators:
            lines.append("\n**Decorators:**\n")
            for decorator in decorators:
                lines.append(f"- `{decorator}`\n")
            lines.append("")

        # Add parameters
        parameters = func.get("parameters", [])
        if parameters:
            lines.append("\n**Parameters:**\n")
            for param in parameters:
                param_name = param.get("name", "unknown")
                param_type = param.get("type", "")
                param_desc = param.get("description", "")
                default = param.get("default")

                param_line = f"- `{param_name}`"
                if param_type:
                    param_line += f" ({param_type})"
                if default is not None:
                    param_line += f" = {default}"

                lines.append(param_line)

                if param_desc:
                    lines.append(f"  - {param_desc}")

            lines.append("")

        # Add return type and description
        return_type = func.get("return_type")
        return_desc = func.get("return_description")

        if return_type or return_desc:
            lines.append("\n**Returns:**\n")
            if return_type:
                lines.append(f"- Type: `{return_type}`")
            if return_desc:
                lines.append(f"- {return_desc}")
            lines.append("")

        # Add examples if present
        examples = func.get("examples", [])
        if examples:
            lines.append("\n**Examples:**\n")
            for example in examples:
                lines.append(f"```python\n{example}\n```")
            lines.append("")

    def _generate_endpoint_docs(
        self,
        endpoint: Dict[str, Any],
        lines: List[str]
    ) -> None:
        """
        Generate documentation for an API endpoint.

        Args:
            endpoint: API endpoint information dictionary
            lines: List to append documentation lines to
        """
        method = endpoint.get("method", "GET").upper()
        path = endpoint.get("path", "/")
        endpoint_name = endpoint.get("name", f"{method} {path}")

        lines.append(f"\n### {endpoint_name}\n")

        # Add endpoint description
        description = endpoint.get("description")
        if description:
            lines.append(f"{description}\n")

        lines.append(f"\n**Method:** `{method}`\n")
        lines.append(f"**Path:** `{path}`\n")

        # Add parameters
        parameters = endpoint.get("parameters", [])
        if parameters:
            lines.append("\n**Parameters:**\n")
            for param in parameters:
                param_name = param.get("name", "unknown")
                param_type = param.get("type", "")
                param_location = param.get("location", "query")  # query, path, body
                required = param.get("required", False)
                param_desc = param.get("description", "")

                param_line = f"- `{param_name}`"
                if param_type:
                    param_line += f" ({param_type})"
                param_line += f" - {param_location}"
                if required:
                    param_line += " (required)"

                lines.append(param_line)

                if param_desc:
                    lines.append(f"  - {param_desc}")

            lines.append("")

        # Add response information
        response = endpoint.get("response", {})
        if response:
            lines.append("\n**Response:**\n")
            response_desc = response.get("description", "")
            if response_desc:
                lines.append(f"{response_desc}\n")

            response_schema = response.get("schema")
            if response_schema:
                lines.append("\n**Schema:**\n")
                lines.append("```json")
                lines.append(response_schema)
                lines.append("```")
                lines.append("")

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
