"""
Test Runner - Run various types of tests.

Executes unit tests, integration tests, linting, and other quality checks.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    LINT = "lint"
    TYPE_CHECK = "type_check"
    SECURITY = "security"
    COVERAGE = "coverage"


@dataclass
class TestResult:
    """Result of running a test."""
    test_type: TestType
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    tests_run: int = 0
    tests_failed: int = 0
    tests_passed: int = 0
    coverage_percent: float = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class TestRunner:
    """
    Runs various types of tests and quality checks.

    Supports:
    - Jest/pytest for unit tests
    - ESLint for linting
    - TypeScript for type checking
    - Custom test commands
    """

    def __init__(self, working_dir: Path = None):
        self.working_dir = working_dir or Path.cwd()

    def run_all_tests(self, test_types: List[TestType] = None) -> Dict[TestType, TestResult]:
        """
        Run all specified test types.

        Args:
            test_types: List of test types to run (default: all)

        Returns:
            Dictionary mapping test type to result
        """
        if test_types is None:
            test_types = [
                TestType.LINT,
                TestType.TYPE_CHECK,
                TestType.UNIT,
                TestType.COVERAGE,
            ]

        results = {}

        for test_type in test_types:
            result = self.run_test(test_type)
            results[test_type] = result

        return results

    def run_test(self, test_type: TestType, **kwargs) -> TestResult:
        """
        Run a specific type of test.

        Args:
            test_type: Type of test to run
            **kwargs: Additional parameters for the test

        Returns:
            TestResult object
        """
        import time

        start_time = time.time()

        try:
            if test_type == TestType.UNIT:
                result = self._run_unit_tests(**kwargs)
            elif test_type == TestType.INTEGRATION:
                result = self._run_integration_tests(**kwargs)
            elif test_type == TestType.E2E:
                result = self._run_e2e_tests(**kwargs)
            elif test_type == TestType.LINT:
                result = self._run_lint(**kwargs)
            elif test_type == TestType.TYPE_CHECK:
                result = self._run_type_check(**kwargs)
            elif test_type == TestType.SECURITY:
                result = self._run_security_check(**kwargs)
            elif test_type == TestType.COVERAGE:
                result = self._run_coverage(**kwargs)
            else:
                result = TestResult(
                    test_type=test_type,
                    success=False,
                    exit_code=1,
                    stdout="",
                    stderr=f"Unknown test type: {test_type}",
                    duration=0,
                )

            result.duration = time.time() - start_time
            return result

        except Exception as e:
            return TestResult(
                test_type=test_type,
                success=False,
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start_time,
            )

    def _run_command(self, command: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=self.working_dir
        )

        return result.returncode, result.stdout, result.stderr

    def _run_unit_tests(self) -> TestResult:
        """Run unit tests."""
        # Detect test framework
        if (self.working_dir / "package.json").exists():
            return self._run_jest_tests()
        elif (self.working_dir / "pytest.ini").exists() or (self.working_dir / "setup.py").exists():
            return self._run_pytest_tests()
        else:
            # Default to npm test
            return self._run_npm_test()

    def _run_jest_tests(self) -> TestResult:
        """Run Jest tests."""
        exit_code, stdout, stderr = self._run_command([
            "npm", "test", "--", "--json", "--outputFile=test-results.json"
        ])

        # Parse results
        try:
            results_file = self.working_dir / "test-results.json"
            if results_file.exists():
                with open(results_file) as f:
                    data = json.load(f)

                return TestResult(
                    test_type=TestType.UNIT,
                    success=exit_code == 0,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration=0,
                    tests_run=data.get("numTotalTests", 0),
                    tests_failed=data.get("numFailedTests", 0),
                    tests_passed=data.get("numPassedTests", 0),
                )
        except Exception:
            pass

        return TestResult(
            test_type=TestType.UNIT,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=0,
        )

    def _run_pytest_tests(self) -> TestResult:
        """Run pytest tests."""
        exit_code, stdout, stderr = self._run_command([
            "pytest", "-v", "--tb=short"
        ])

        # Parse output
        tests_run = 0
        tests_passed = 0
        tests_failed = 0

        for line in stdout.split('\n'):
            if " passed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        tests_passed = int(parts[i-1])
                    elif part == "failed":
                        tests_failed = int(parts[i-1])

        tests_run = tests_passed + tests_failed

        return TestResult(
            test_type=TestType.UNIT,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=0,
            tests_run=tests_run,
            tests_failed=tests_failed,
            tests_passed=tests_passed,
        )

    def _run_npm_test(self) -> TestResult:
        """Run generic npm test."""
        exit_code, stdout, stderr = self._run_command(["npm", "test"])

        return TestResult(
            test_type=TestType.UNIT,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=0,
        )

    def _run_integration_tests(self) -> TestResult:
        """Run integration tests."""
        exit_code, stdout, stderr = self._run_command([
            "npm", "run", "test:integration"
        ])

        return TestResult(
            test_type=TestType.INTEGRATION,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=0,
        )

    def _run_e2e_tests(self) -> TestResult:
        """Run end-to-end tests."""
        exit_code, stdout, stderr = self._run_command([
            "npm", "run", "test:e2e"
        ])

        return TestResult(
            test_type=TestType.E2E,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=0,
        )

    def _run_lint(self) -> TestResult:
        """Run linter."""
        if (self.working_dir / "package.json").exists():
            exit_code, stdout, stderr = self._run_command(["npm", "run", "lint"])

            # Count errors/warnings
            errors = []
            for line in stdout.split('\n'):
                if 'error' in line.lower() or 'warning' in line.lower():
                    errors.append(line.strip())

            return TestResult(
                test_type=TestType.LINT,
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=0,
                errors=errors,
            )
        else:
            return TestResult(
                test_type=TestType.LINT,
                success=True,
                exit_code=0,
                stdout="No linter configured",
                stderr="",
                duration=0,
            )

    def _run_type_check(self) -> TestResult:
        """Run TypeScript type checking."""
        if (self.working_dir / "tsconfig.json").exists():
            exit_code, stdout, stderr = self._run_command(["npx", "tsc", "--noEmit"])

            return TestResult(
                test_type=TestType.TYPE_CHECK,
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=0,
            )
        else:
            return TestResult(
                test_type=TestType.TYPE_CHECK,
                success=True,
                exit_code=0,
                stdout="No TypeScript configuration",
                stderr="",
                duration=0,
            )

    def _run_security_check(self) -> TestResult:
        """Run security audit."""
        if (self.working_dir / "package.json").exists():
            exit_code, stdout, stderr = self._run_command(["npm", "audit", "--json"])

            try:
                audit_data = json.loads(stdout)
                vulnerabilities = audit_data.get("metadata", {}).get("vulnerabilities", {})

                total_vulns = sum(vulnerabilities.values())
                high_vulns = vulnerabilities.get("high", 0) + vulnerabilities.get("critical", 0)

                return TestResult(
                    test_type=TestType.SECURITY,
                    success=high_vulns == 0,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration=0,
                    errors=[f"{total_vulns} vulnerabilities found"] if total_vulns > 0 else [],
                )
            except json.JSONDecodeError:
                return TestResult(
                    test_type=TestType.SECURITY,
                    success=True,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration=0,
                )
        else:
            return TestResult(
                test_type=TestType.SECURITY,
                success=True,
                exit_code=0,
                stdout="No package.json",
                stderr="",
                duration=0,
            )

    def _run_coverage(self) -> TestResult:
        """Run test coverage analysis."""
        if (self.working_dir / "package.json").exists():
            exit_code, stdout, stderr = self._run_command([
                "npm", "test", "--", "--coverage", "--coverageReporters=json"
            ])

            # Parse coverage
            try:
                coverage_file = self.working_dir / "coverage" / "coverage-final.json"
                if coverage_file.exists():
                    with open(coverage_file) as f:
                        data = json.load(f)

                    total = data.get("total", {})
                    lines_pct = total.get("lines", {}).get("pct", 0)

                    return TestResult(
                        test_type=TestType.COVERAGE,
                        success=lines_pct >= 80,
                        exit_code=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                        duration=0,
                        coverage_percent=lines_pct,
                    )
            except Exception:
                pass

        return TestResult(
            test_type=TestType.COVERAGE,
            success=False,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=0,
        )
