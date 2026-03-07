"""
Error Detector - Detect and analyze test failures.

Identifies patterns in test failures and provides actionable feedback.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .test_runner import TestResult, TestType


class ErrorCategory(Enum):
    """Categories of errors."""
    SYNTAX = "syntax"
    IMPORT = "import"
    TYPE = "type"
    LOGIC = "logic"
    ASSERTION = "assertion"
    TIMEOUT = "timeout"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Information about an error."""
    category: ErrorCategory
    message: str
    file_path: str = None
    line_number: int = None
    code_snippet: str = None
    suggested_fix: str = None
    confidence: float = 0.0


class ErrorDetector:
    """
    Detects and analyzes test failures.

    Features:
    - Parse error messages
    - Categorize errors
    - Extract relevant context
    - Suggest potential fixes
    """

    def __init__(self):
        # Patterns for error detection
        self.patterns = {
            ErrorCategory.SYNTAX: [
                r"SyntaxError",
                r"Unexpected token",
                r"Unexpected identifier",
                r"Missing.*before.*",
            ],
            ErrorCategory.IMPORT: [
                r"Cannot find module",
                r"Module not found",
                r"ImportError",
                r"No module named",
            ],
            ErrorCategory.TYPE: [
                r"TypeError",
                r"is not a function",
                r"is not defined",
                r"Cannot read property",
                r"Type '.*' is not assignable",
            ],
            ErrorCategory.ASSERTION: [
                r"AssertionError",
                r"Expected.*to.*",
                r"assert.*failed",
            ],
            ErrorCategory.TIMEOUT: [
                r"Timeout",
                r"exceeded.*timeout",
            ],
            ErrorCategory.DEPENDENCY: [
                r"ECONNREFUSED",
                r"Connection refused",
                r"Network error",
            ],
            ErrorCategory.CONFIGURATION: [
                r"ConfigError",
                r"Configuration error",
            ],
        }

    def detect_errors(self, test_result: TestResult) -> List[ErrorInfo]:
        """
        Detect errors in a test result.

        Args:
            test_result: Test result to analyze

        Returns:
            List of ErrorInfo objects
        """
        if test_result.success:
            return []

        errors = []

        # Parse stderr for errors
        errors.extend(self._parse_errors(test_result.stderr))

        # Parse stdout for errors
        errors.extend(self._parse_errors(test_result.stdout))

        return errors

    def _parse_errors(self, output: str) -> List[ErrorInfo]:
        """Parse error messages from output."""
        errors = []

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Detect error category
            category = self._categorize_error(line)

            if category != ErrorCategory.UNKNOWN:
                error_info = ErrorInfo(
                    category=category,
                    message=line,
                    confidence=self._calculate_confidence(line, category),
                )

                # Extract file path and line number
                file_match = re.search(r'at\s+(.+?):(\d+)', line)
                if file_match:
                    error_info.file_path = file_match.group(1)
                    error_info.line_number = int(file_match.group(2))

                # Generate suggested fix
                error_info.suggested_fix = self._suggest_fix(category, line)

                errors.append(error_info)

        return errors

    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """Categorize an error message."""
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return category

        return ErrorCategory.UNKNOWN

    def _calculate_confidence(self, error_message: str, category: ErrorCategory) -> float:
        """Calculate confidence in error categorization."""
        # Base confidence
        confidence = 0.5

        # Increase confidence for specific patterns
        if category != ErrorCategory.UNKNOWN:
            confidence += 0.2

        # Increase confidence for well-formed error messages
        if ":" in error_message and len(error_message) > 20:
            confidence += 0.1

        # Increase confidence if stack trace is present
        if "at " in error_message or "Error:" in error_message:
            confidence += 0.2

        return min(confidence, 1.0)

    def _suggest_fix(self, category: ErrorCategory, error_message: str) -> str:
        """Suggest a fix for an error."""
        suggestions = {
            ErrorCategory.SYNTAX: "Check syntax in the referenced file. Look for missing brackets, semicolons, or operators.",
            ErrorCategory.IMPORT: "Verify the module path and ensure the dependency is installed.",
            ErrorCategory.TYPE: "Check the type of the variable/object. Ensure it matches the expected type.",
            ErrorCategory.ASSERTION: "Review the test assertion. The actual value does not match the expected value.",
            ErrorCategory.TIMEOUT: "The test is taking too long. Consider increasing timeout or optimizing the code.",
            ErrorCategory.DEPENDENCY: "Check if external services are running and accessible.",
            ErrorCategory.CONFIGURATION: "Verify configuration files and environment variables.",
        }

        base_suggestion = suggestions.get(category, "Review the error message and stack trace for more details.")

        # Add specific suggestions based on error message
        if "Cannot find module" in error_message:
            module_match = re.search(r"'([^']+)'", error_message)
            if module_match:
                module_name = module_match.group(1)
                return f"{base_suggestion} Try running: npm install {module_name}"

        return base_suggestion

    def get_error_summary(self, errors: List[ErrorInfo]) -> Dict[str, Any]:
        """Get a summary of errors."""
        if not errors:
            return {
                "total_errors": 0,
                "by_category": {},
                "high_confidence": 0,
            }

        by_category = {}
        high_confidence = 0

        for error in errors:
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1

            if error.confidence >= 0.7:
                high_confidence += 1

        return {
            "total_errors": len(errors),
            "by_category": by_category,
            "high_confidence": high_confidence,
            "most_common": max(by_category.items(), key=lambda x: x[1])[0] if by_category else None,
        }

    def prioritize_errors(self, errors: List[ErrorInfo]) -> List[ErrorInfo]:
        """Prioritize errors by importance."""
        # Priority order
        priority_order = {
            ErrorCategory.SYNTAX: 1,
            ErrorCategory.IMPORT: 2,
            ErrorCategory.TYPE: 3,
            ErrorCategory.CONFIGURATION: 4,
            ErrorCategory.DEPENDENCY: 5,
            ErrorCategory.LOGIC: 6,
            ErrorCategory.ASSERTION: 7,
            ErrorCategory.TIMEOUT: 8,
            ErrorCategory.UNKNOWN: 9,
        }

        # Sort by priority and confidence
        return sorted(
            errors,
            key=lambda e: (priority_order.get(e.category, 99), -e.confidence)
        )
