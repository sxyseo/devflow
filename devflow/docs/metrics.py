"""
Documentation Metrics - Calculate and track documentation coverage and quality.

Measures documentation coverage, quality scores, and generates reports
to help maintain high-quality documentation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import json


class MetricType(Enum):
    """Types of documentation metrics."""
    COVERAGE = "coverage"
    QUALITY = "quality"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    FRESHNESS = "freshness"
    TRENDS = "trends"


class ElementType(Enum):
    """Types of code elements to track."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    API_ENDPOINT = "api_endpoint"
    PARAMETER = "parameter"
    RETURN_VALUE = "return_value"


@dataclass
class CoverageMetric:
    """Documentation coverage metric for a specific element."""
    element_type: ElementType
    total: int
    documented: int
    coverage_percentage: float
    file_path: str = None

    def __post_init__(self):
        """Calculate coverage percentage."""
        if self.total > 0:
            self.coverage_percentage = (self.documented / self.total) * 100
        else:
            self.coverage_percentage = 0.0


@dataclass
class QualityMetric:
    """Quality metric for documentation."""
    element_type: ElementType
    element_name: str
    file_path: str
    line_number: int
    has_docstring: bool
    docstring_length: int = 0
    has_parameters: bool = False
    has_return_type: bool = False
    has_examples: bool = False
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    freshness_score: float = 0.0
    overall_score: float = 0.0


@dataclass
class MetricsReport:
    """Complete metrics report for a codebase."""
    timestamp: str
    codebase_path: str
    coverage_metrics: Dict[str, CoverageMetric] = field(default_factory=dict)
    quality_metrics: List[QualityMetric] = field(default_factory=list)
    overall_coverage: float = 0.0
    overall_quality: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricTrend:
    """Trend data for metrics over time."""
    timestamp: str
    coverage_percentage: float
    quality_score: float
    total_elements: int
    documented_elements: int


class DocumentationMetrics:
    """
    Calculate and track documentation metrics.

    Features:
    - Calculate documentation coverage for different element types
    - Assess quality scores (completeness, accuracy, freshness)
    - Generate comprehensive metrics reports
    - Track metrics trends over time
    - Provide recommendations for improving documentation
    """

    def __init__(self):
        """Initialize the documentation metrics calculator."""
        self.history: List[MetricTrend] = []
        self.quality_weights = {
            "completeness": 0.4,
            "accuracy": 0.3,
            "freshness": 0.3,
        }

    def calculate_coverage(
        self,
        codebase_path: str,
        element_types: Optional[List[ElementType]] = None
    ) -> Dict[str, CoverageMetric]:
        """
        Calculate documentation coverage for specified element types.

        Args:
            codebase_path: Path to the codebase to analyze
            element_types: List of element types to calculate coverage for.
                         If None, calculates for all types.

        Returns:
            Dictionary mapping element type names to CoverageMetric objects

        Raises:
            FileNotFoundError: If the codebase path doesn't exist
        """
        path = Path(codebase_path)

        if not path.exists():
            raise FileNotFoundError(f"Codebase path not found: {codebase_path}")

        if element_types is None:
            element_types = [
                ElementType.FUNCTION,
                ElementType.CLASS,
                ElementType.METHOD,
                ElementType.MODULE,
            ]

        coverage_results = {}

        # Import analyzer to extract code information
        try:
            from devflow.docs.analyzer import DocumentationAnalyzer
            analyzer = DocumentationAnalyzer()
        except ImportError:
            raise ImportError(
                "DocumentationAnalyzer not found. "
                "Ensure devflow.docs.analyzer is available."
            )

        # Calculate coverage for each element type
        for element_type in element_types:
            total, documented = self._count_elements(path, analyzer, element_type)
            metric = CoverageMetric(
                element_type=element_type,
                total=total,
                documented=documented,
                coverage_percentage=0.0,  # Will be calculated in __post_init__
            )
            coverage_results[element_type.value] = metric

        return coverage_results

    def calculate_quality_score(
        self,
        elements: List[Dict[str, Any]]
    ) -> List[QualityMetric]:
        """
        Calculate quality scores for documentation elements.

        Args:
            elements: List of element dictionaries from the analyzer

        Returns:
            List of QualityMetric objects with calculated scores
        """
        quality_metrics = []

        for element in elements:
            metric = QualityMetric(
                element_type=self._get_element_type(element),
                element_name=element.get("name", "unknown"),
                file_path=element.get("file_path", ""),
                line_number=element.get("line_number", 0),
                has_docstring=element.get("docstring") is not None,
                docstring_length=len(element.get("docstring", "")),
                has_parameters=len(element.get("parameters", [])) > 0,
                has_return_type=element.get("return_type") is not None,
                has_examples=self._has_examples(element),
            )

            # Calculate individual scores
            metric.completeness_score = self._calculate_completeness(metric)
            metric.accuracy_score = self._calculate_accuracy(metric)
            metric.freshness_score = self._calculate_freshness(metric)

            # Calculate overall score using weights
            metric.overall_score = (
                metric.completeness_score * self.quality_weights["completeness"] +
                metric.accuracy_score * self.quality_weights["accuracy"] +
                metric.freshness_score * self.quality_weights["freshness"]
            )

            quality_metrics.append(metric)

        return quality_metrics

    def generate_report(
        self,
        codebase_path: str,
        include_recommendations: bool = True
    ) -> MetricsReport:
        """
        Generate a comprehensive metrics report.

        Args:
            codebase_path: Path to the codebase to analyze
            include_recommendations: Whether to include improvement recommendations

        Returns:
            MetricsReport object with all metrics and recommendations

        Raises:
            FileNotFoundError: If the codebase path doesn't exist
        """
        path = Path(codebase_path)

        if not path.exists():
            raise FileNotFoundError(f"Codebase path not found: {codebase_path}")

        # Calculate coverage metrics
        coverage_metrics = self.calculate_coverage(codebase_path)

        # Calculate overall coverage
        total_elements = sum(m.total for m in coverage_metrics.values())
        total_documented = sum(m.documented for m in coverage_metrics.values())
        overall_coverage = (
            (total_documented / total_elements * 100) if total_elements > 0 else 0.0
        )

        # Collect all elements for quality assessment
        elements = self._collect_elements(path)
        quality_metrics = self.calculate_quality_score(elements)

        # Calculate overall quality
        if quality_metrics:
            overall_quality = sum(m.overall_score for m in quality_metrics) / len(quality_metrics)
        else:
            overall_quality = 0.0

        # Create report
        report = MetricsReport(
            timestamp=datetime.now().isoformat(),
            codebase_path=str(path),
            coverage_metrics=coverage_metrics,
            quality_metrics=quality_metrics,
            overall_coverage=overall_coverage,
            overall_quality=overall_quality,
        )

        # Add recommendations if requested
        if include_recommendations:
            report.recommendations = self._generate_recommendations(report)

        # Add metadata
        report.metadata = {
            "total_elements_analyzed": total_elements,
            "total_documented_elements": total_documented,
            "element_types_count": len(coverage_metrics),
            "quality_metrics_count": len(quality_metrics),
        }

        # Store trend data
        self._record_trend(report)

        return report

    def get_trends(self, limit: int = 10) -> List[MetricTrend]:
        """
        Get metrics trends over time.

        Args:
            limit: Maximum number of trend records to return

        Returns:
            List of MetricTrend objects ordered by timestamp (most recent first)
        """
        return sorted(self.history, key=lambda t: t.timestamp, reverse=True)[:limit]

    def save_report(self, report: MetricsReport, output_path: str) -> None:
        """
        Save a metrics report to a JSON file.

        Args:
            report: MetricsReport to save
            output_path: Path where the report should be saved

        Raises:
            IOError: If the file cannot be written
        """
        try:
            report_dict = {
                "timestamp": report.timestamp,
                "codebase_path": report.codebase_path,
                "coverage_metrics": {
                    k: {
                        "element_type": v.element_type.value,
                        "total": v.total,
                        "documented": v.documented,
                        "coverage_percentage": v.coverage_percentage,
                        "file_path": v.file_path,
                    }
                    for k, v in report.coverage_metrics.items()
                },
                "quality_metrics": [
                    {
                        "element_type": m.element_type.value,
                        "element_name": m.element_name,
                        "file_path": m.file_path,
                        "line_number": m.line_number,
                        "has_docstring": m.has_docstring,
                        "docstring_length": m.docstring_length,
                        "has_parameters": m.has_parameters,
                        "has_return_type": m.has_return_type,
                        "has_examples": m.has_examples,
                        "completeness_score": m.completeness_score,
                        "accuracy_score": m.accuracy_score,
                        "freshness_score": m.freshness_score,
                        "overall_score": m.overall_score,
                    }
                    for m in report.quality_metrics
                ],
                "overall_coverage": report.overall_coverage,
                "overall_quality": report.overall_quality,
                "recommendations": report.recommendations,
                "metadata": report.metadata,
            }

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2)

        except Exception as e:
            raise IOError(f"Failed to save report to {output_path}: {e}")

    def load_report(self, input_path: str) -> MetricsReport:
        """
        Load a metrics report from a JSON file.

        Args:
            input_path: Path to the report file

        Returns:
            MetricsReport object

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            coverage_metrics = {}
            for k, v in data["coverage_metrics"].items():
                coverage_metrics[k] = CoverageMetric(
                    element_type=ElementType(v["element_type"]),
                    total=v["total"],
                    documented=v["documented"],
                    coverage_percentage=v["coverage_percentage"],
                    file_path=v.get("file_path"),
                )

            quality_metrics = []
            for m in data["quality_metrics"]:
                quality_metrics.append(QualityMetric(
                    element_type=ElementType(m["element_type"]),
                    element_name=m["element_name"],
                    file_path=m["file_path"],
                    line_number=m["line_number"],
                    has_docstring=m["has_docstring"],
                    docstring_length=m["docstring_length"],
                    has_parameters=m["has_parameters"],
                    has_return_type=m["has_return_type"],
                    has_examples=m["has_examples"],
                    completeness_score=m["completeness_score"],
                    accuracy_score=m["accuracy_score"],
                    freshness_score=m["freshness_score"],
                    overall_score=m["overall_score"],
                ))

            return MetricsReport(
                timestamp=data["timestamp"],
                codebase_path=data["codebase_path"],
                coverage_metrics=coverage_metrics,
                quality_metrics=quality_metrics,
                overall_coverage=data["overall_coverage"],
                overall_quality=data["overall_quality"],
                recommendations=data.get("recommendations", []),
                metadata=data.get("metadata", {}),
            )

        except FileNotFoundError:
            raise FileNotFoundError(f"Report file not found: {input_path}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid report format in {input_path}: {e}")

    def _count_elements(
        self,
        path: Path,
        analyzer,
        element_type: ElementType
    ) -> tuple[int, int]:
        """
        Count total and documented elements of a specific type.

        Args:
            path: Path to the codebase
            analyzer: DocumentationAnalyzer instance
            element_type: Type of element to count

        Returns:
            Tuple of (total_count, documented_count)
        """
        total = 0
        documented = 0

        # Find all relevant files
        if element_type in [ElementType.FUNCTION, ElementType.CLASS, ElementType.METHOD]:
            files = list(path.rglob("*.py"))
            for file_path in files:
                try:
                    result = analyzer.analyze_python_file(str(file_path))

                    if element_type == ElementType.FUNCTION:
                        elements = result.get("functions", [])
                    elif element_type == ElementType.CLASS:
                        elements = result.get("classes", [])
                    elif element_type == ElementType.METHOD:
                        # Count methods within classes
                        elements = []
                        for cls in result.get("classes", []):
                            elements.extend(cls.get("methods", []))

                    total += len(elements)
                    documented += sum(1 for e in elements if e.get("docstring"))

                except Exception:
                    # Skip files that can't be analyzed
                    continue

        elif element_type == ElementType.MODULE:
            files = list(path.rglob("*.py"))
            total = len(files)
            documented = sum(1 for f in files if self._has_module_doc(f))

        return total, documented

    def _has_module_doc(self, file_path: Path) -> bool:
        """Check if a Python file has a module docstring."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple check for module docstring
                import ast
                tree = ast.parse(content, filename=str(file_path))
                return ast.get_docstring(tree) is not None
        except Exception:
            return False

    def _collect_elements(self, path: Path) -> List[Dict[str, Any]]:
        """Collect all elements from the codebase for quality assessment."""
        elements = []

        try:
            from devflow.docs.analyzer import DocumentationAnalyzer
            analyzer = DocumentationAnalyzer()
        except ImportError:
            return elements

        # Analyze Python files
        for file_path in path.rglob("*.py"):
            try:
                result = analyzer.analyze_python_file(str(file_path))

                # Add functions
                for func in result.get("functions", []):
                    elements.append({
                        "name": func.get("name"),
                        "type": "function",
                        "file_path": str(file_path),
                        "line_number": func.get("line_number"),
                        "docstring": func.get("docstring"),
                        "parameters": func.get("parameters", []),
                        "return_type": func.get("return_type"),
                    })

                # Add classes
                for cls in result.get("classes", []):
                    elements.append({
                        "name": cls.get("name"),
                        "type": "class",
                        "file_path": str(file_path),
                        "line_number": cls.get("line_number"),
                        "docstring": cls.get("docstring"),
                        "parameters": [],
                        "return_type": None,
                    })

            except Exception:
                continue

        return elements

    def _get_element_type(self, element: Dict[str, Any]) -> ElementType:
        """Get ElementType from element dictionary."""
        element_type = element.get("type", "unknown")

        type_mapping = {
            "function": ElementType.FUNCTION,
            "class": ElementType.CLASS,
            "method": ElementType.METHOD,
            "module": ElementType.MODULE,
            "api_endpoint": ElementType.API_ENDPOINT,
        }

        return type_mapping.get(element_type, ElementType.FUNCTION)

    def _has_examples(self, element: Dict[str, Any]) -> bool:
        """Check if element documentation has examples."""
        docstring = element.get("docstring", "")
        if not docstring:
            return False

        # Simple heuristic: look for "Example" or "Examples" in docstring
        example_keywords = ["example", "examples", ">>>", "usage"]
        docstring_lower = docstring.lower()
        return any(keyword in docstring_lower for keyword in example_keywords)

    def _calculate_completeness(self, metric: QualityMetric) -> float:
        """Calculate completeness score (0-100)."""
        score = 0.0

        if metric.has_docstring:
            score += 30

        if metric.docstring_length > 50:
            score += 20

        if metric.has_parameters:
            score += 15

        if metric.has_return_type:
            score += 15

        if metric.has_examples:
            score += 20

        return min(score, 100.0)

    def _calculate_accuracy(self, metric: QualityMetric) -> float:
        """Calculate accuracy score (0-100)."""
        # This is a placeholder - actual accuracy would require more sophisticated analysis
        # For now, base it on docstring presence and length
        if not metric.has_docstring:
            return 0.0

        score = 50.0  # Base score for having a docstring

        if metric.docstring_length > 100:
            score += 30

        if metric.has_parameters and metric.has_return_type:
            score += 20

        return min(score, 100.0)

    def _calculate_freshness(self, metric: QualityMetric) -> float:
        """Calculate freshness score (0-100)."""
        # This is a placeholder - actual freshness would require git history analysis
        # For now, return a default score
        return 100.0

    def _generate_recommendations(self, report: MetricsReport) -> List[str]:
        """Generate improvement recommendations based on metrics."""
        recommendations = []

        # Coverage recommendations
        if report.overall_coverage < 50:
            recommendations.append(
                "Documentation coverage is below 50%. "
                "Prioritize adding docstrings to all functions and classes."
            )
        elif report.overall_coverage < 75:
            recommendations.append(
                "Documentation coverage is below 75%. "
                "Focus on documenting undocumented elements."
            )

        # Quality recommendations
        if report.overall_quality < 60:
            recommendations.append(
                "Documentation quality is low. "
                "Enhance existing docstrings with parameter descriptions "
                "and return value documentation."
            )

        # Check for missing examples
        elements_with_examples = sum(
            1 for m in report.quality_metrics if m.has_examples
        )
        if report.quality_metrics and elements_with_examples / len(report.quality_metrics) < 0.3:
            recommendations.append(
                "Most documentation lacks examples. "
                "Add usage examples to improve documentation quality."
            )

        # Type-specific recommendations
        for element_type, metric in report.coverage_metrics.items():
            if metric.coverage_percentage < 50:
                recommendations.append(
                    f"{element_type} coverage is low ({metric.coverage_percentage:.1f}%). "
                    f"Focus on documenting {element_type}s."
                )

        return recommendations

    def _record_trend(self, report: MetricsReport) -> None:
        """Record metrics data for trend tracking."""
        total_elements = sum(m.total for m in report.coverage_metrics.values())
        documented_elements = sum(m.documented for m in report.coverage_metrics.values())

        trend = MetricTrend(
            timestamp=report.timestamp,
            coverage_percentage=report.overall_coverage,
            quality_score=report.overall_quality,
            total_elements=total_elements,
            documented_elements=documented_elements,
        )

        self.history.append(trend)

        # Keep only last 100 trends to avoid excessive memory usage
        if len(self.history) > 100:
            self.history = self.history[-100:]
