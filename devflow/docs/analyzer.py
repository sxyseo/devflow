"""
Documentation Analyzer - Extract documentation information from code.

Analyzes Python and JavaScript/TypeScript code to extract functions,
classes, docstrings, and other documentation-relevant information.
"""

import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DocumentationType(Enum):
    """Types of documentation elements."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    API_ENDPOINT = "api_endpoint"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"
    EXAMPLE = "example"
    UNKNOWN = "unknown"


class ChangeType(Enum):
    """Types of changes detected in code."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    NO_CHANGE = "no_change"


@dataclass
class DocumentationElement:
    """A documentation element extracted from code."""
    type: DocumentationType
    name: str
    file_path: str
    line_number: int
    docstring: str = None
    signature: str = None
    parameters: List[Dict[str, Any]] = None
    return_type: str = None
    decorators: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values for lists."""
        if self.parameters is None:
            self.parameters = []
        if self.decorators is None:
            self.decorators = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CodeChange:
    """A change detected between code snapshots."""
    change_type: ChangeType
    element_type: DocumentationType
    element_name: str
    file_path: str
    old_value: str = None
    new_value: str = None
    line_number: int = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


class DocumentationAnalyzer:
    """
    Analyzes code to extract documentation information.

    Features:
    - Parse Python code using AST
    - Parse JavaScript/TypeScript code
    - Extract functions, classes, and docstrings
    - Detect changes between code versions
    - Identify API endpoints and their signatures
    """

    def __init__(self):
        """Initialize the documentation analyzer."""
        # Patterns for JavaScript/TypeScript parsing
        self.js_patterns = {
            "function": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>|(?:async\s+)?function))",
            "class": r"class\s+(\w+)",
            "method": r"(\w+)\s*\([^)]*\)\s*{",
            "jsdoc": r"/\*\*[\s\S]*?\*/",
        }

    def analyze_python_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a Python file and extract documentation information.

        Args:
            file_path: Path to the Python file

        Returns:
            Dictionary containing extracted documentation elements

        Raises:
            FileNotFoundError: If the file doesn't exist
            SyntaxError: If the file has invalid Python syntax
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.suffix == ".py":
            raise ValueError(f"Not a Python file: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                source_code = f.read()

            tree = ast.parse(source_code, filename=str(path))

            result = {
                "file_path": str(path),
                "module_docstring": ast.get_docstring(tree),
                "functions": [],
                "classes": [],
                "imports": [],
            }

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append({
                            "module": alias.name,
                            "alias": alias.asname,
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        result["imports"].append({
                            "module": f"{module}.{alias.name}",
                            "alias": alias.asname,
                        })

            # Extract top-level functions
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    func_info = self._extract_function_info(node, str(path))
                    result["functions"].append(func_info)
                elif isinstance(node, ast.ClassDef):
                    class_info = self._extract_class_info(node, str(path))
                    result["classes"].append(class_info)

            return result

        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in {file_path}: {e}")

    def analyze_javascript_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a JavaScript/TypeScript file and extract documentation information.

        Args:
            file_path: Path to the JavaScript/TypeScript file

        Returns:
            Dictionary containing extracted documentation elements

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        valid_extensions = [".js", ".jsx", ".ts", ".tsx"]
        if path.suffix not in valid_extensions:
            raise ValueError(f"Not a JavaScript/TypeScript file: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            source_code = f.read()

        result = {
            "file_path": str(path),
            "functions": [],
            "classes": [],
            "comments": [],
        }

        # Extract functions
        for match in re.finditer(self.js_patterns["function"], source_code):
            func_name = match.group(1) or match.group(2)
            if func_name:
                result["functions"].append({
                    "name": func_name,
                    "line_number": source_code[:match.start()].count("\n") + 1,
                })

        # Extract classes
        for match in re.finditer(self.js_patterns["class"], source_code):
            class_name = match.group(1)
            result["classes"].append({
                "name": class_name,
                "line_number": source_code[:match.start()].count("\n") + 1,
            })

        # Extract JSDoc comments
        for match in re.finditer(self.js_patterns["jsdoc"], source_code):
            docstring = match.group(0).strip()
            result["comments"].append({
                "content": docstring,
                "line_number": source_code[:match.start()].count("\n") + 1,
            })

        return result

    def detect_changes(
        self,
        old_code: str,
        new_code: str,
        file_path: str
    ) -> List[CodeChange]:
        """
        Detect changes between two versions of code.

        Args:
            old_code: Original code content
            new_code: Modified code content
            file_path: Path to the file

        Returns:
            List of detected changes
        """
        changes = []

        # Parse old code
        try:
            old_elements = self._extract_code_elements(old_code, file_path)
        except Exception:
            old_elements = []

        # Parse new code
        try:
            new_elements = self._extract_code_elements(new_code, file_path)
        except Exception:
            new_elements = []

        # Create lookup dictionaries
        old_by_name = {e["name"]: e for e in old_elements}
        new_by_name = {e["name"]: e for e in new_elements}

        old_names = set(old_by_name.keys())
        new_names = set(new_by_name.keys())

        # Detect added elements
        added_names = new_names - old_names
        for name in added_names:
            element = new_by_name[name]
            element_type = self._get_element_type(element)
            changes.append(CodeChange(
                change_type=ChangeType.ADDED,
                element_type=element_type,
                element_name=name,
                file_path=file_path,
                new_value=element.get("signature", ""),
                line_number=element.get("line_number"),
            ))

        # Detect deleted elements
        deleted_names = old_names - new_names
        for name in deleted_names:
            element = old_by_name[name]
            element_type = self._get_element_type(element)
            changes.append(CodeChange(
                change_type=ChangeType.DELETED,
                element_type=element_type,
                element_name=name,
                file_path=file_path,
                old_value=element.get("signature", ""),
                line_number=element.get("line_number"),
            ))

        # Detect modified elements
        common_names = old_names & new_names
        for name in common_names:
            old_element = old_by_name[name]
            new_element = new_by_name[name]

            # Compare signatures
            if old_element.get("signature") != new_element.get("signature"):
                element_type = self._get_element_type(new_element)
                changes.append(CodeChange(
                    change_type=ChangeType.MODIFIED,
                    element_type=element_type,
                    element_name=name,
                    file_path=file_path,
                    old_value=old_element.get("signature", ""),
                    new_value=new_element.get("signature", ""),
                    line_number=new_element.get("line_number"),
                ))

        return changes

    def compare_snapshots(
        self,
        old_snapshot: Dict[str, Any],
        new_snapshot: Dict[str, Any]
    ) -> List[CodeChange]:
        """
        Compare two code snapshots and detect changes.

        Args:
            old_snapshot: Previous code snapshot
            new_snapshot: New code snapshot

        Returns:
            List of detected changes across all files
        """
        all_changes = []

        # Get all file paths
        old_files = set(old_snapshot.keys())
        new_files = set(new_snapshot.keys())

        # Detect new files
        for file_path in new_files - old_files:
            all_changes.append(CodeChange(
                change_type=ChangeType.ADDED,
                element_type=DocumentationType.MODULE,
                element_name=file_path,
                file_path=file_path,
                new_value="<new file>",
            ))

        # Detect deleted files
        for file_path in old_files - new_files:
            all_changes.append(CodeChange(
                change_type=ChangeType.DELETED,
                element_type=DocumentationType.MODULE,
                element_name=file_path,
                file_path=file_path,
                old_value="<deleted file>",
            ))

        # Compare common files
        for file_path in old_files & new_files:
            old_code = old_snapshot[file_path]
            new_code = new_snapshot[file_path]

            if old_code != new_code:
                file_changes = self.detect_changes(old_code, new_code, file_path)
                all_changes.extend(file_changes)

        return all_changes

    def _get_element_type(self, element: Dict[str, Any]) -> DocumentationType:
        """
        Get documentation type from element.

        Args:
            element: Element dictionary

        Returns:
            DocumentationType enum value
        """
        element_type = element.get("type", "unknown")

        type_mapping = {
            "function": DocumentationType.FUNCTION,
            "class": DocumentationType.CLASS,
            "method": DocumentationType.METHOD,
            "module": DocumentationType.MODULE,
        }

        return type_mapping.get(element_type, DocumentationType.UNKNOWN)

    def _extract_function_info(
        self,
        node: ast.FunctionDef,
        file_path: str
    ) -> Dict[str, Any]:
        """Extract information from a function AST node."""
        info = {
            "name": node.name,
            "line_number": node.lineno,
            "docstring": ast.get_docstring(node),
            "parameters": [],
            "return_type": None,
            "decorators": [],
        }

        # Extract parameters
        for arg in node.args.args:
            param_info = {
                "name": arg.arg,
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            }
            info["parameters"].append(param_info)

        # Extract return type
        if node.returns:
            info["return_type"] = ast.unparse(node.returns)

        # Extract decorators
        for decorator in node.decorator_list:
            info["decorators"].append(ast.unparse(decorator))

        return info

    def _extract_class_info(
        self,
        node: ast.ClassDef,
        file_path: str
    ) -> Dict[str, Any]:
        """Extract information from a class AST node."""
        info = {
            "name": node.name,
            "line_number": node.lineno,
            "docstring": ast.get_docstring(node),
            "methods": [],
            "decorators": [],
        }

        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_function_info(item, file_path)
                info["methods"].append(method_info)

        # Extract decorators
        for decorator in node.decorator_list:
            info["decorators"].append(ast.unparse(decorator))

        return info

    def _extract_code_elements(
        self,
        code: str,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """Extract code elements for change detection."""
        elements = []

        try:
            tree = ast.parse(code, filename=file_path)

            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    elements.append({
                        "name": node.name,
                        "line_number": node.lineno,
                        "type": "function",
                        "signature": ast.unparse(node),
                    })
                elif isinstance(node, ast.ClassDef):
                    elements.append({
                        "name": node.name,
                        "line_number": node.lineno,
                        "type": "class",
                        "signature": ast.unparse(node),
                    })
        except Exception:
            pass

        return elements
