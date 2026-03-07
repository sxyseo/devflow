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

        if not changes:
            return False

        try:
            # Read existing README content
            original_content = readme.read_text(encoding="utf-8")

            # Parse and update README sections
            updated_content = self._update_readme_sections(
                original_content,
                changes,
                analyzed_code
            )

            # Only write if content actually changed
            if updated_content != original_content:
                readme.write_text(updated_content, encoding="utf-8")
                return True

            return False

        except Exception as e:
            raise IOError(f"Failed to update README at {readme_path}: {e}")

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

        # Determine diagram directory
        if diagram_dir:
            target_dir = Path(diagram_dir)
        else:
            target_dir = self._output_dir / "diagrams"

        # Ensure directory exists
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise IOError(f"Failed to create diagram directory {target_dir}: {e}")

        diagrams = []

        # Generate different types of architecture diagrams
        # 1. Module dependency diagram
        module_diagram = self._generate_module_diagram(code_structure, target_dir)
        if module_diagram:
            diagrams.append(module_diagram)

        # 2. Class hierarchy diagram
        class_diagram = self._generate_class_diagram(code_structure, target_dir)
        if class_diagram:
            diagrams.append(class_diagram)

        # 3. Component interaction diagram
        component_diagram = self._generate_component_diagram(
            code_structure,
            target_dir
        )
        if component_diagram:
            diagrams.append(component_diagram)

        return diagrams

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

    def _update_readme_sections(
        self,
        content: str,
        changes: List[Any],
        analyzed_code: Dict[str, Any] = None
    ) -> str:
        """
        Update README sections with code changes and analyzed information.

        Args:
            content: Original README content
            changes: List of code changes to document
            analyzed_code: Optional analyzed code information

        Returns:
            Updated README content
        """
        lines = content.split("\n")
        updated_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this is a section that might need updates
            if line.startswith("##") and not line.startswith("###"):
                section_title = line.lstrip("#").strip().lower()

                # Handle different section types
                if section_title in ["features", "what's new", "changelog", "changes"]:
                    # Update features/changelog section
                    updated_lines.append(line)
                    i += 1

                    # Skip existing content until next section
                    section_content = []
                    while i < len(lines) and not lines[i].startswith("##"):
                        section_content.append(lines[i])
                        i += 1

                    # Add new changes at the beginning of the section
                    new_changes = self._format_changes_for_readme(changes)
                    if new_changes:
                        updated_lines.append(new_changes)
                        if section_content and section_content[0].strip():
                            updated_lines.append("")

                    updated_lines.extend(section_content)
                    continue

                elif section_title in ["installation", "getting started", "usage"]:
                    # Update installation/usage section if analyzed code provides new info
                    updated_lines.append(line)
                    i += 1

                    # Skip existing content
                    while i < len(lines) and not lines[i].startswith("##"):
                        updated_lines.append(lines[i])
                        i += 1
                    continue

                elif section_title in ["api reference", "documentation", "docs"]:
                    # Update API reference section
                    updated_lines.append(line)
                    i += 1

                    # Skip existing content
                    while i < len(lines) and not lines[i].startswith("##"):
                        updated_lines.append(lines[i])
                        i += 1
                    continue

            updated_lines.append(line)
            i += 1

        # Add changelog section if it doesn't exist and there are changes
        if changes and not any(line.lower().startswith("## changelog") or
                             line.lower().startswith("## changes") or
                             line.lower().startswith("## what's new")
                             for line in lines):
            updated_lines.append("")
            updated_lines.append("## Changelog")
            updated_lines.append("")
            new_changes = self._format_changes_for_readme(changes)
            if new_changes:
                updated_lines.append(new_changes)

        return "\n".join(updated_lines)

    def _format_changes_for_readme(self, changes: List[Any]) -> str:
        """
        Format code changes for README documentation.

        Args:
            changes: List of code changes

        Returns:
            Formatted changes as Markdown
        """
        if not changes:
            return ""

        lines = []

        # Group changes by type
        added = []
        modified = []
        removed = []

        for change in changes:
            if isinstance(change, dict):
                change_type = change.get("type", "").lower()
                change_desc = change.get("description", "")

                if change_type == "added":
                    added.append(change_desc)
                elif change_type == "modified":
                    modified.append(change_desc)
                elif change_type == "removed":
                    removed.append(change_desc)
            elif isinstance(change, str):
                # Simple string changes, treat as additions
                added.append(change)

        # Format changes by type
        if added:
            lines.append("### Added")
            lines.append("")
            for item in added:
                lines.append(f"- {item}")
            lines.append("")

        if modified:
            lines.append("### Modified")
            lines.append("")
            for item in modified:
                lines.append(f"- {item}")
            lines.append("")

        if removed:
            lines.append("### Removed")
            lines.append("")
            for item in removed:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines).strip()

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

    def _generate_module_diagram(
        self,
        code_structure: Dict[str, Any],
        target_dir: Path
    ) -> Optional[ArchitectureDiagram]:
        """
        Generate a module dependency diagram using Mermaid.

        Args:
            code_structure: Code structure dictionary
            target_dir: Directory to save the diagram

        Returns:
            ArchitectureDiagram object or None if no modules to diagram
        """
        # Extract module information
        modules = self._extract_modules(code_structure)
        if not modules:
            return None

        # Build Mermaid graph
        lines = ["graph TD"]
        lines.append("    %% Module Dependency Diagram")

        # Add nodes for each module
        for module in modules:
            module_name = module.get("name", "unknown")
            module_id = f"module_{module_name.replace('.', '_')}"
            lines.append(f"    {module_id}[\"{module_name}\"]")

        # Add edges for dependencies
        for module in modules:
            module_name = module.get("name", "unknown")
            module_id = f"module_{module_name.replace('.', '_')}"

            dependencies = module.get("dependencies", [])
            for dep in dependencies:
                dep_id = f"module_{dep.replace('.', '_')}"
                lines.append(f"    {module_id} --> {dep_id}")

        # Add styling
        lines.append("")
        lines.append("    classDef moduleStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px;")
        lines.append("    class module_.* moduleStyle;")

        content = "\n".join(lines)
        file_path = target_dir / "module_dependencies.mmd"

        # Write diagram file
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise IOError(f"Failed to write module diagram: {e}")

        return ArchitectureDiagram(
            diagram_type="mermaid",
            content=content,
            file_path=str(file_path),
            metadata={
                "title": "Module Dependencies",
                "description": "Shows module dependencies in the codebase",
                "module_count": len(modules),
            },
        )

    def _generate_class_diagram(
        self,
        code_structure: Dict[str, Any],
        target_dir: Path
    ) -> Optional[ArchitectureDiagram]:
        """
        Generate a class hierarchy diagram using Mermaid.

        Args:
            code_structure: Code structure dictionary
            target_dir: Directory to save the diagram

        Returns:
            ArchitectureDiagram object or None if no classes to diagram
        """
        # Extract class information
        classes = self._extract_classes(code_structure)
        if not classes:
            return None

        # Build Mermaid class diagram
        lines = ["classDiagram"]
        lines.append("    %% Class Hierarchy Diagram")

        # Add class definitions
        for cls in classes:
            class_name = cls.get("name", "Unknown")
            lines.append(f"    class {class_name} {{")

            # Add methods
            methods = cls.get("methods", [])
            if methods:
                for method in methods:
                    method_name = method.get("name", "unknown")
                    lines.append(f"        +{method_name}()")
                lines.append("    }")
            else:
                lines.append("    }")

        # Add inheritance relationships
        for cls in classes:
            class_name = cls.get("name", "Unknown")
            base_class = cls.get("base_class")

            if base_class:
                lines.append(f"    {base_class} <|-- {class_name}")

        # Add composition/aggregation relationships
        for cls in classes:
            class_name = cls.get("name", "Unknown")
            associations = cls.get("associations", [])

            for assoc in associations:
                assoc_type = assoc.get("type", "association")
                target_class = assoc.get("target")

                if assoc_type == "composition":
                    lines.append(f"    {class_name} *-- {target_class}")
                elif assoc_type == "aggregation":
                    lines.append(f"    {class_name} o-- {target_class}")
                else:
                    lines.append(f"    {class_name} --> {target_class}")

        content = "\n".join(lines)
        file_path = target_dir / "class_hierarchy.mmd"

        # Write diagram file
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise IOError(f"Failed to write class diagram: {e}")

        return ArchitectureDiagram(
            diagram_type="mermaid",
            content=content,
            file_path=str(file_path),
            metadata={
                "title": "Class Hierarchy",
                "description": "Shows class relationships and inheritance",
                "class_count": len(classes),
            },
        )

    def _generate_component_diagram(
        self,
        code_structure: Dict[str, Any],
        target_dir: Path
    ) -> Optional[ArchitectureDiagram]:
        """
        Generate a component interaction diagram using Mermaid.

        Args:
            code_structure: Code structure dictionary
            target_dir: Directory to save the diagram

        Returns:
            ArchitectureDiagram object or None if no components to diagram
        """
        # Extract component information
        components = self._extract_components(code_structure)
        if not components:
            return None

        # Build Mermaid flowchart
        lines = ["graph LR"]
        lines.append("    %% Component Interaction Diagram")

        # Add nodes for each component
        for component in components:
            comp_name = component.get("name", "unknown")
            comp_type = component.get("type", "component")
            comp_id = f"comp_{comp_name.replace(' ', '_').lower()}"
            comp_label = f"{comp_name}\\n({comp_type})"
            lines.append(f"    {comp_id}[\"{comp_label}\"]")

        # Add edges for interactions
        for component in components:
            comp_name = component.get("name", "unknown")
            comp_id = f"comp_{comp_name.replace(' ', '_').lower()}"

            interactions = component.get("interactions", [])
            for interaction in interactions:
                target = interaction.get("target")
                label = interaction.get("label", "")

                target_id = f"comp_{target.replace(' ', '_').lower()}"

                if label:
                    lines.append(f"    {comp_id} -->|{label}| {target_id}")
                else:
                    lines.append(f"    {comp_id} --> {target_id}")

        # Add styling
        lines.append("")
        lines.append("    classDef componentStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;")
        lines.append("    classDef serviceStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;")
        lines.append("    classDef databaseStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px;")
        lines.append("    class comp_.* componentStyle;")

        content = "\n".join(lines)
        file_path = target_dir / "component_interaction.mmd"

        # Write diagram file
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise IOError(f"Failed to write component diagram: {e}")

        return ArchitectureDiagram(
            diagram_type="mermaid",
            content=content,
            file_path=str(file_path),
            metadata={
                "title": "Component Interactions",
                "description": "Shows how components interact with each other",
                "component_count": len(components),
            },
        )

    def _extract_modules(self, code_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract module information from code structure.

        Args:
            code_structure: Code structure dictionary

        Returns:
            List of module dictionaries
        """
        modules = []

        # Handle different input formats
        if "files" in code_structure:
            # Multiple files format
            for file_data in code_structure["files"]:
                imports = file_data.get("imports", [])
                file_path = file_data.get("file_path", "")
                module_name = self._path_to_module_name(file_path)

                if module_name:
                    modules.append({
                        "name": module_name,
                        "dependencies": [imp.get("module", "") for imp in imports if imp.get("module")],
                    })
        elif "file_path" in code_structure:
            # Single file format
            imports = code_structure.get("imports", [])
            file_path = code_structure.get("file_path", "")
            module_name = self._path_to_module_name(file_path)

            if module_name:
                modules.append({
                    "name": module_name,
                    "dependencies": [imp.get("module", "") for imp in imports if imp.get("module")],
                })

        return modules

    def _extract_classes(self, code_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract class information from code structure.

        Args:
            code_structure: Code structure dictionary

        Returns:
            List of class dictionaries
        """
        classes = []

        # Handle different input formats
        if "files" in code_structure:
            # Multiple files format
            for file_data in code_structure["files"]:
                file_classes = file_data.get("classes", [])
                for cls in file_classes:
                    classes.append(cls)
        elif "file_path" in code_structure:
            # Single file format
            file_classes = code_structure.get("classes", [])
            for cls in file_classes:
                classes.append(cls)
        elif "classes" in code_structure:
            # Legacy format
            classes = code_structure.get("classes", [])

        return classes

    def _extract_components(self, code_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract component information from code structure.

        Args:
            code_structure: Code structure dictionary

        Returns:
            List of component dictionaries
        """
        components = []

        # Analyze classes to determine components
        classes = self._extract_classes(code_structure)

        for cls in classes:
            class_name = cls.get("name", "Unknown")

            # Determine component type based on naming patterns
            comp_type = "component"
            if "Service" in class_name or "service" in class_name:
                comp_type = "service"
            elif "Repository" in class_name or "repository" in class_name:
                comp_type = "repository"
            elif "Controller" in class_name or "controller" in class_name:
                comp_type = "controller"
            elif "Model" in class_name or "model" in class_name:
                comp_type = "model"
            elif "Database" in class_name or "database" in class_name:
                comp_type = "database"

            # Extract interactions from methods
            interactions = []
            methods = cls.get("methods", [])
            for method in methods:
                method_name = method.get("name", "")
                # Simple heuristic: if method calls other components, add interaction
                if "call" in method_name.lower() or "get" in method_name.lower() or "fetch" in method_name.lower():
                    # This is a simplified analysis - in practice, you'd parse method bodies
                    pass

            components.append({
                "name": class_name,
                "type": comp_type,
                "interactions": interactions,
            })

        return components

    def _path_to_module_name(self, file_path: str) -> str:
        """
        Convert file path to module name.

        Args:
            file_path: File path string

        Returns:
            Module name string
        """
        path = Path(file_path)

        # Remove file extension
        name = path.stem

        # Join with parent directories if within a package
        parts = path.parent.parts
        if parts and "src" in parts:
            src_idx = parts.index("src")
            package_parts = parts[src_idx + 1:]
            if package_parts:
                name = ".".join(package_parts) + "." + name

        return name
