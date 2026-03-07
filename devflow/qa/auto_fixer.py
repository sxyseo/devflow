"""
Auto Fixer - Automatically fix common errors.

Attempts to fix detected errors using AI agents.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .error_detector import ErrorInfo, ErrorCategory
from ..core.session_manager import SessionManager


@dataclass
class FixAttempt:
    """Result of a fix attempt."""
    error: ErrorInfo
    fix_applied: bool
    fix_description: str
    files_modified: List[str]
    success: bool
    retry_needed: bool = False


class AutoFixer:
    """
    Automatically fixes common errors.

    Features:
    - Syntax error fixes
    - Import statement fixes
    - Type error fixes
    - Configuration fixes
    - AI-powered intelligent fixes for complex errors
    """

    def __init__(self, session_manager: SessionManager, working_dir: Path = None):
        self.sessions = session_manager
        self.working_dir = working_dir or Path.cwd()

    def fix_errors(self, errors: List[ErrorInfo], max_fixes: int = 5) -> List[FixAttempt]:
        """
        Attempt to fix a list of errors.

        Args:
            errors: List of errors to fix
            max_fixes: Maximum number of fixes to attempt

        Returns:
            List of FixAttempt objects
        """
        fix_attempts = []

        for error in errors[:max_fixes]:
            attempt = self.fix_error(error)
            fix_attempts.append(attempt)

            if attempt.retry_needed:
                # Fix might need another iteration
                pass

        return fix_attempts

    def fix_error(self, error: ErrorInfo) -> FixAttempt:
        """
        Attempt to fix a single error.

        Args:
            error: Error to fix

        Returns:
            FixAttempt object
        """
        try:
            if error.category == ErrorCategory.SYNTAX:
                return self._fix_syntax_error(error)
            elif error.category == ErrorCategory.IMPORT:
                return self._fix_import_error(error)
            elif error.category == ErrorCategory.TYPE:
                return self._fix_type_error(error)
            elif error.category == ErrorCategory.CONFIGURATION:
                return self._fix_configuration_error(error)
            else:
                # Use AI for complex fixes
                return self._fix_with_ai(error)

        except Exception as e:
            return FixAttempt(
                error=error,
                fix_applied=False,
                fix_description=f"Failed to apply fix: {str(e)}",
                files_modified=[],
                success=False,
            )

    def _fix_syntax_error(self, error: ErrorInfo) -> FixAttempt:
        """Attempt to fix syntax errors."""
        if not error.file_path:
            return FixAttempt(
                error=error,
                fix_applied=False,
                fix_description="No file path provided",
                files_modified=[],
                success=False,
            )

        file_path = self.working_dir / error.file_path

        if not file_path.exists():
            return FixAttempt(
                error=error,
                fix_applied=False,
                fix_description=f"File not found: {file_path}",
                files_modified=[],
                success=False,
            )

        # Read file content
        content = file_path.read_text()
        original_content = content

        # Apply common syntax fixes
        fixes_applied = []

        # Fix: Missing semicolons (basic)
        if "Missing" in error.message and "semicolon" in error.message.lower():
            # Add semicolons after statements (simplified)
            content = re.sub(r'([a-zA-Z0-9_)]\n)', r'\1;\n', content)
            fixes_applied.append("Added missing semicolons")

        # Fix: Missing closing brackets
        if "Expected" in error.message and ("}" in error.message or ")" in error.message or "]" in error.message):
            # Count brackets and add missing ones (simplified)
            open_braces = content.count('{')
            close_braces = content.count('}')

            if open_braces > close_braces:
                content += '\n' + '}' * (open_braces - close_braces)
                fixes_applied.append(f"Added {open_braces - close_braces} missing closing braces")

        # Write back if changed
        if content != original_content:
            file_path.write_text(content)

            return FixAttempt(
                error=error,
                fix_applied=True,
                fix_description=f"Syntax fixes applied: {', '.join(fixes_applied)}",
                files_modified=[str(file_path)],
                success=True,
                retry_needed=True,
            )

        return FixAttempt(
            error=error,
            fix_applied=False,
            fix_description="No applicable syntax fix found",
            files_modified=[],
            success=False,
        )

    def _fix_import_error(self, error: ErrorInfo) -> FixAttempt:
        """Attempt to fix import errors."""
        # Extract module name from error
        module_match = re.search(r"'([^']+)'", error.message)

        if not module_match:
            return FixAttempt(
                error=error,
                fix_applied=False,
                fix_description="Could not extract module name",
                files_modified=[],
                success=False,
            )

        module_name = module_match.group(1)

        # Try to install the module
        import subprocess

        try:
            # Determine package manager
            if (self.working_dir / "package.json").exists():
                # Node.js project
                result = subprocess.run(
                    ["npm", "install", module_name],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=60
                )

                if result.returncode == 0:
                    return FixAttempt(
                        error=error,
                        fix_applied=True,
                        fix_description=f"Installed {module_name} via npm",
                        files_modified=["package.json", "package-lock.json"],
                        success=True,
                        retry_needed=False,
                    )

            elif (self.working_dir / "requirements.txt").exists() or (self.working_dir / "setup.py").exists():
                # Python project
                package_name = module_name.replace('-', '_')

                result = subprocess.run(
                    ["pip", "install", package_name],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=60
                )

                if result.returncode == 0:
                    return FixAttempt(
                        error=error,
                        fix_applied=True,
                        fix_description=f"Installed {package_name} via pip",
                        files_modified=[],
                        success=True,
                        retry_needed=False,
                    )

        except Exception as e:
            return FixAttempt(
                error=error,
                fix_applied=False,
                fix_description=f"Failed to install module: {str(e)}",
                files_modified=[],
                success=False,
            )

        return FixAttempt(
            error=error,
            fix_applied=False,
            fix_description=f"Could not install module: {module_name}",
            files_modified=[],
            success=False,
        )

    def _fix_type_error(self, error: ErrorInfo) -> FixAttempt:
        """Attempt to fix type errors."""
        # Type errors usually require code changes
        # Use AI for intelligent fixes
        return self._fix_with_ai(error)

    def _fix_configuration_error(self, error: ErrorInfo) -> FixAttempt:
        """Attempt to fix configuration errors."""
        # Check for common config issues
        fixes_applied = []

        # Example: Create missing config files
        if "tsconfig.json" in error.message or "TypeScript" in error.message:
            tsconfig_path = self.working_dir / "tsconfig.json"

            if not tsconfig_path.exists():
                # Create basic TypeScript config
                default_config = {
                    "compilerOptions": {
                        "target": "ES2020",
                        "module": "commonjs",
                        "lib": ["ES2020"],
                        "strict": True,
                        "esModuleInterop": True,
                        "skipLibCheck": True,
                        "forceConsistentCasingInFileNames": True,
                        "outDir": "./dist",
                        "rootDir": "./src",
                    },
                    "include": ["src/**/*"],
                    "exclude": ["node_modules"],
                }

                import json
                with open(tsconfig_path, 'w') as f:
                    json.dump(default_config, f, indent=2)

                fixes_applied.append("Created tsconfig.json")

        if fixes_applied:
            return FixAttempt(
                error=error,
                fix_applied=True,
                fix_description=f"Configuration fixes applied: {', '.join(fixes_applied)}",
                files_modified=[str(f) for f in fixes_applied],
                success=True,
                retry_needed=True,
            )

        return FixAttempt(
            error=error,
            fix_applied=False,
            fix_description="No applicable configuration fix found",
            files_modified=[],
            success=False,
        )

    def _fix_with_ai(self, error: ErrorInfo) -> FixAttempt:
        """Use AI agent to fix complex errors."""
        # Create a prompt for the AI agent
        prompt = f"""# Task: Fix Error

## Error Message
{error.message}

## Error Category
{error.category.value}

## Suggested Fix
{error.suggested_fix}

## File
{error.file_path}:{error.line_number if error.line_number else 'unknown'}

Please analyze this error and provide a fix. If you can identify the specific code that needs to be changed, make the modification. If you need more context, request it.

Return your response in the following format:
```
FIX_APPLIED: true/false
FIX_DESCRIPTION: Your description
FILES_MODIFIED: List of modified files
CODE_CHANGES: Specific code changes made
```
"""

        try:
            # Spawn AI agent session
            session = self.sessions.create_session(
                agent_id=f"fixer-{error.category.value}",
                agent_type="fixer",
                task=prompt
            )

            # Monitor for completion
            # (In real implementation, would poll for completion)
            # For now, return attempt info

            return FixAttempt(
                error=error,
                fix_applied=False,  # Will be updated when agent completes
                fix_description=f"AI fixer agent spawned (session: {session.name})",
                files_modified=[],
                success=False,  # Will be updated based on result
                retry_needed=True,
            )

        except Exception as e:
            return FixAttempt(
                error=error,
                fix_applied=False,
                fix_description=f"Failed to spawn AI fixer: {str(e)}",
                files_modified=[],
                success=False,
            )

    def verify_fix(self, error: ErrorInfo, fix_attempt: FixAttempt) -> bool:
        """Verify that a fix was successful."""
        # Re-run tests to verify fix
        # This is a simplified version
        # In real implementation, would re-run specific test

        if not fix_attempt.files_modified:
            return False

        return True  # Placeholder
