"""
QA Loop - Automated testing and fixing loop.

Continuously tests, detects errors, and fixes them in a loop.
"""

import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .test_runner import TestRunner, TestType, TestResult
from .error_detector import ErrorDetector, ErrorInfo
from .auto_fixer import AutoFixer, FixAttempt
from ..core.state_tracker import StateTracker


class QALoopStatus(Enum):
    """Status of the QA loop."""
    IDLE = "idle"
    TESTING = "testing"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


@dataclass
class QALoopResult:
    """Result of a QA loop iteration."""
    iteration: int
    status: QALoopStatus
    test_results: Dict[TestType, TestResult]
    errors_detected: List[ErrorInfo]
    fixes_attempted: List[FixAttempt]
    tests_passed: bool
    duration: float
    error_message: str = None


class QALoop:
    """
    Automated QA loop that tests, detects errors, and fixes them.

    The loop continues until:
    - All tests pass
    - Maximum iterations reached
    - Unfixable error encountered
    """

    def __init__(self, state_tracker: StateTracker, session_manager,
                 working_dir = None, max_iterations: int = 3):
        self.state = state_tracker
        self.runner = TestRunner(working_dir)
        self.detector = ErrorDetector()
        self.fixer = AutoFixer(session_manager, working_dir)
        self.max_iterations = max_iterations
        self._running = False
        self._callbacks: List[Callable[[QALoopResult], None]] = []

    def add_callback(self, callback: Callable[[QALoopResult], None]):
        """Add a callback to be called after each iteration."""
        self._callbacks.append(callback)

    def run(self, test_types: List[TestType] = None) -> QALoopResult:
        """
        Run the QA loop to completion.

        Args:
            test_types: List of test types to run (default: all)

        Returns:
            Final QALoopResult
        """
        iteration = 0
        all_passed = False

        while iteration < self.max_iterations and not all_passed:
            iteration += 1

            # Run one iteration
            result = self.run_iteration(iteration, test_types)

            # Notify callbacks
            for callback in self._callbacks:
                callback(result)

            # Check if tests passed
            all_passed = result.tests_passed

            # Stop if failed or max iterations reached
            if result.status in [QALoopStatus.FAILED, QALoopStatus.MAX_ITERATIONS_REACHED]:
                break

        # Return final result
        return result

    def run_iteration(self, iteration: int, test_types: List[TestType] = None) -> QALoopResult:
        """
        Run a single QA loop iteration.

        Args:
            iteration: Iteration number
            test_types: List of test types to run

        Returns:
            QALoopResult for this iteration
        """
        start_time = time.time()

        try:
            # Phase 1: Run tests
            print(f"\n🔍 Iteration {iteration}: Running tests...")
            test_results = self.runner.run_all_tests(test_types)

            # Check if all tests passed
            all_passed = all(r.success for r in test_results.values())

            if all_passed:
                print(f"✓ All tests passed!")
                return QALoopResult(
                    iteration=iteration,
                    status=QALoopStatus.COMPLETED,
                    test_results=test_results,
                    errors_detected=[],
                    fixes_attempted=[],
                    tests_passed=True,
                    duration=time.time() - start_time,
                )

            # Phase 2: Detect errors
            print(f"⚠️  Tests failed. Detecting errors...")
            all_errors = []

            for test_type, result in test_results.items():
                if not result.success:
                    errors = self.detector.detect_errors(result)
                    all_errors.extend(errors)

            if not all_errors:
                print(f"✗ No specific errors detected, but tests failed")
                return QALoopResult(
                    iteration=iteration,
                    status=QALoopStatus.FAILED,
                    test_results=test_results,
                    errors_detected=[],
                    fixes_attempted=[],
                    tests_passed=False,
                    duration=time.time() - start_time,
                    error_message="Tests failed but no specific errors detected",
                )

            print(f"  Detected {len(all_errors)} errors")

            # Phase 3: Prioritize errors
            prioritized_errors = self.detector.prioritize_errors(all_errors)

            # Phase 4: Attempt fixes
            print(f"🔧 Attempting to fix {len(prioritized_errors)} errors...")
            fixes_attempted = self.fixer.fix_errors(prioritized_errors)

            successful_fixes = sum(1 for f in fixes_attempted if f.fix_applied)
            print(f"  Applied {successful_fixes}/{len(fixes_attempted)} fixes")

            # Return result
            return QALoopResult(
                iteration=iteration,
                status=QALoopStatus.FIXING,
                test_results=test_results,
                errors_detected=all_errors,
                fixes_attempted=fixes_attempted,
                tests_passed=False,
                duration=time.time() - start_time,
            )

        except Exception as e:
            print(f"✗ QA loop failed: {e}")
            return QALoopResult(
                iteration=iteration,
                status=QALoopStatus.FAILED,
                test_results={},
                errors_detected=[],
                fixes_attempted=[],
                tests_passed=False,
                duration=time.time() - start_time,
                error_message=str(e),
            )

    def run_async(self, test_types: List[TestType] = None,
                 on_complete: Callable[[QALoopResult], None] = None):
        """
        Run the QA loop asynchronously.

        Args:
            test_types: List of test types to run
            on_complete: Callback when loop completes
        """
        def loop_thread():
            result = self.run(test_types)

            if on_complete:
                on_complete(result)

        thread = threading.Thread(target=loop_thread, daemon=True)
        thread.start()

        return thread

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the QA loop."""
        return {
            "running": self._running,
            "max_iterations": self.max_iterations,
            "callbacks_registered": len(self._callbacks),
        }
