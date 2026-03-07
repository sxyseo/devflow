# Documentation Generator Skill

## Purpose
Automatically generate and maintain documentation for code changes, API endpoints, and system architecture. Keep documentation in sync with code through intelligent analysis and incremental updates.

## When to Use
- After implementing new features or APIs
- When code refactoring changes interfaces
- Before releasing new versions
- When documentation drift is detected
- For onboarding new team members
- During code review processes

## Inputs
- Source code directory path
- Documentation types to generate (api, readme, architecture)
- Configuration options (force_update, generate_metrics)
- Existing documentation files (for incremental updates)

## Outputs
- Generated API documentation (Markdown)
- Updated README files
- Synchronized architecture diagrams (Mermaid)
- Documentation coverage metrics report
- Documentation task proposals for gaps
- Quality assessment reports

## Process

### 1. Initialize Documentation Generator
```bash
# Import the documentation generator agent
from agents.doc_generator import DocumentationGeneratorAgent

# Create agent instance with project path
agent = DocumentationGeneratorAgent(project_path="./devflow")
```

Verify agent initialization:
```bash
# Check that analyzer and generator components are loaded
print(f"Analyzer: {agent.analyzer}")
print(f"Generator: {agent.generator}")
print(f"Metrics Tracker: {agent.metrics_tracker}")
```

### 2. Analyze Codebase Structure

#### 2.1. Scan Project Files
```bash
# Create generation request
from agents.doc_generator import DocGenerationRequest

request = DocGenerationRequest(
    source_path="./devflow",
    output_path="./docs",
    doc_types=["api", "readme", "architecture"],
    force_update=False,
    generate_metrics=True
)

# Scan source directory for code files
analysis_result = agent.analyze_codebase(request.source_path)
```

Verify scan results:
```bash
# Check discovered files
files = analysis_result.get('files', [])
print(f"Found {len(files)} files to analyze")

# Display file breakdown by type
from collections import Counter
file_types = Counter(f.suffix for f in files)
for ext, count in file_types.most_common():
    print(f"  {ext}: {count} files")
```

#### 2.2. Extract Code Structure
```bash
# Parse AST and extract documentation-relevant information
for file_path in files:
    try:
        ast_info = agent.analyzer._parse_file(file_path)
        classes = agent.analyzer._extract_classes(ast_info)
        functions = agent.analyzer._extract_functions(ast_info)
        print(f"{file_path}: {len(classes)} classes, {len(functions)} functions")
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
```

### 3. Detect Changes and Gaps

#### 3.1. Compare with Existing Documentation
```bash
# Detect files that lack documentation
gaps = agent.detect_documentation_gaps(request.source_path)

# Categorize gaps by type
gap_types = {}
for gap in gaps:
    gap_type = gap['type']
    if gap_type not in gap_types:
        gap_types[gap_type] = []
    gap_types[gap_type].append(gap)

# Display summary
for gap_type, items in gap_types.items():
    print(f"{gap_type}: {len(items)} gaps")
```

#### 3.2. Identify Changed Files (Incremental Mode)
```bash
# For incremental updates, detect recently modified files
import os
import time

cutoff_time = time.time() - (24 * 3600)  # Last 24 hours
changed_files = []

for file_path in files:
    mtime = os.path.getmtime(file_path)
    if mtime > cutoff_time:
        changed_files.append(file_path)

print(f"Detected {len(changed_files)} recently changed files")
```

### 4. Generate Documentation

#### 4.1. Prepare Output Directory
```bash
# Ensure output directory exists
import os
os.makedirs(request.output_path, exist_ok=True)

# Set up subdirectories for different doc types
for doc_type in request.doc_types:
    type_dir = os.path.join(request.output_path, doc_type)
    os.makedirs(type_dir, exist_ok=True)
```

#### 4.2. Generate API Documentation
```bash
# Generate API docs for all discovered functions and classes
if "api" in request.doc_types:
    api_result = agent._generate_api_docs(analysis_result)

    # Verify generated files
    for doc_file in api_result.files_generated:
        print(f"Generated: {doc_file}")
        # Check file size (should be non-zero)
        file_size = os.path.getsize(doc_file)
        print(f"  Size: {file_size} bytes")
```

#### 4.3. Generate README Documentation
```bash
# Generate or update README with project overview
if "readme" in request.doc_types:
    readme_result = agent._generate_readme_docs(analysis_result)

    # Verify README structure
    readme_path = os.path.join(request.output_path, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, 'r') as f:
            content = f.read()
            print(f"README generated: {len(content)} characters")
            # Check for required sections
            required_sections = ["## Overview", "## Installation", "## Usage"]
            for section in required_sections:
                if section in content:
                    print(f"  ✓ {section} present")
                else:
                    print(f"  ✗ {section} missing")
```

#### 4.4. Generate Architecture Diagrams
```bash
# Generate Mermaid diagrams showing system architecture
if "architecture" in request.doc_types:
    arch_result = agent._generate_architecture_docs(analysis_result)

    # Validate Mermaid syntax
    for doc_file in arch_result.files_generated:
        if doc_file.endswith('.md'):
            with open(doc_file, 'r') as f:
                content = f.read()
                if '```mermaid' in content:
                    print(f"✓ Mermaid diagram in {doc_file}")
```

### 5. Validate Quality

#### 5.1. Validate Generated Files
```bash
# Run validation phase
validation_result = agent._validate_phase(request)

# Check validation results
if validation_result.success:
    print("✓ All generated files validated successfully")
else:
    print("✗ Validation errors found:")
    for error in validation_result.errors:
        print(f"  - {error.file_path}: {error.message}")
```

#### 5.2. Check Documentation Completeness
```bash
# Verify all public APIs are documented
for file_path in files:
    ast_info = agent.analyzer._parse_file(file_path)
    classes = agent.analyzer._extract_classes(ast_info)
    functions = agent.analyzer._extract_functions(ast_info)

    # Check for missing docstrings
    for cls in classes:
        if not cls.docstring:
            print(f"Warning: Class {cls.name} lacks docstring in {file_path}")

    for func in functions:
        if not func.docstring:
            print(f"Warning: Function {func.name} lacks docstring in {file_path}")
```

### 6. Update Metrics

#### 6.1. Calculate Coverage Metrics
```bash
# Generate metrics report if requested
if request.generate_metrics:
    metrics = agent._calculate_metrics(request)

    # Display key metrics
    print(f"Documentation Coverage: {metrics.get('coverage', 'N/A')}")
    print(f"Quality Score: {metrics.get('quality_score', 'N/A')}")
    print(f"Freshness Score: {metrics.get('freshness', 'N/A')}")
```

#### 6.2. Save Metrics Report
```bash
# Write metrics to file for tracking trends
metrics_path = os.path.join(request.output_path, "metrics.json")
with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"Metrics saved to: {metrics_path}")
```

#### 6.3. Track Trends Over Time
```bash
# Compare with previous metrics
from devflow.docs.metrics import DocumentationMetrics

tracker = DocumentationMetrics()
current_metrics = tracker.generate_report(request.source_path)
trends = tracker.get_trends(current_metrics)

if trends:
    print("\nMetrics Trends:")
    for metric, trend in trends.items():
        direction = "↑" if trend > 0 else "↓"
        print(f"  {metric}: {direction} {abs(trend):.1f}%")
```

### 7. Handle Optional Tasks

#### 7.1. Propose Documentation Tasks
```bash
# Generate tasks for missing documentation
tasks = agent.propose_documentation_tasks(request.source_path)

# Sort by priority
priority_order = {"high": 0, "medium": 1, "low": 2}
tasks_sorted = sorted(tasks, key=lambda t: priority_order.get(t.priority, 3))

# Display top priority tasks
print("\nTop Priority Documentation Tasks:")
for task in tasks_sorted[:5]:
    print(f"  [{task.priority.upper()}] {task.type}")
    print(f"    {task.suggested_action}")
```

#### 7.2. Create Task Files (Optional)
```bash
# Write tasks to file for review
tasks_dir = "./.taskmaster/docs-tasks"
os.makedirs(tasks_dir, exist_ok=True)

for task in tasks_sorted:
    task_file = os.path.join(tasks_dir, f"{task.task_id}.md")
    with open(task_file, 'w') as f:
        f.write(f"# Documentation Task: {task.task_id}\n\n")
        f.write(f"**Type:** {task.type}\n")
        f.write(f"**Priority:** {task.priority}\n")
        f.write(f"**File:** {task.file_path}\n\n")
        f.write(f"## Action Required\n\n{task.suggested_action}\n")

print(f"Created {len(tasks)} task files in {tasks_dir}")
```

### 8. Commit Generated Documentation

#### 8.1. Review Generated Files
```bash
# Display summary of changes
print("\nGenerated Documentation Summary:")
print(f"  Total files: {len(result.files_generated)}")
print(f"  API docs: {len([f for f in result.files_generated if 'api' in f])}")
print(f"  READMEs: {len([f for f in result.files_generated if 'README' in f])}")
print(f"  Architecture: {len([f for f in result.files_generated if 'architecture' in f])}")
print(f"  Duration: {result.duration:.2f}s")
```

#### 8.2. Stage and Commit
```bash
# Add generated documentation to git
git add ./docs

# Create commit with descriptive message
git commit -m "docs: auto-generated documentation

- Generated API documentation for public interfaces
- Updated README with current project structure
- Synchronized architecture diagrams
- Coverage: ${metrics.get('coverage', 'N/A')}
- Quality Score: ${metrics.get('quality_score', 'N/A')}

Co-Authored-By: Claude Documentation Generator"
```

## Quality Standards

### Documentation Coverage
- [ ] API documentation covers all public functions and classes
- [ ] README files accurately reflect current functionality
- [ ] Architecture diagrams match actual code structure
- [ ] All parameters and return values are documented
- [ ] Examples provided for complex APIs

### Documentation Quality
- [ ] Docstrings follow project style guide
- [ ] Documentation is clear and concise
- [ ] Examples are accurate and runnable
- [ ] Cross-references are valid
- [ ] No broken links or references

### Metrics Standards
- [ ] Coverage metric ≥ 80% for documented elements
- [ ] Quality score ≥ 7.0/10 for generated docs
- [ ] Freshness score reflects recent code changes
- [ ] Trend data shows improvement over time
- [ ] Metrics report is generated and saved

### Workflow Standards
- [ ] All phases complete without errors
- [ ] Incremental updates detect changes correctly
- [ ] Generated files are valid Markdown
- [ ] Documentation tasks are prioritized appropriately
- [ ] Performance is acceptable (< 60s for typical projects)

## HALT Conditions

Return HALT if:
- **Missing analyzer**: `HALT: DocumentationAnalyzer not available | Context: Ensure devflow.docs.analyzer is installed and accessible`
- **Generator failure**: `HALT: DocumentationGenerator failed | Context: Check generator configuration and output path permissions`
- **Analysis errors**: `HALT: Code analysis failed | Context: Verify source path exists and contains valid code files`
- **Validation failure**: `HALT: Generated documentation invalid | Context: Review validation errors and check generator output`
- **Metrics calculation error**: `HALT: Metrics calculation failed | Context: Check metrics module and data consistency`
- **File system errors**: `HALT: Cannot write documentation files | Context: Verify output directory exists and is writable`
- **Import errors**: `HALT: Required dependencies missing | Context: Install required packages (ast, json5 for JS support)`

## Example Workflow

```bash
# Basic documentation generation
python -c "
from agents.doc_generator import DocumentationGeneratorAgent

agent = DocumentationGeneratorAgent()
result = agent.run_generation_workflow(
    source_path='./devflow',
    output_path='./docs',
    doc_types=['api', 'readme']
)

print(f'Generated {len(result.files_generated)} files')
print(f'Status: {result.status.value}')
"

# Incremental update for ongoing development
python -c "
from agents.doc_generator import DocumentationGeneratorAgent

agent = DocumentationGeneratorAgent()
result = agent.incremental_update(
    source_path='./devflow',
    doc_types=['api']
)

print(f'Updated {len(result.files_generated)} changed files')
print(f'Changes detected: {result.metrics[\"changes_detected\"]}')
"

# Generate metrics report
python -c "
from agents.doc_generator import DocumentationGeneratorAgent
from devflow.docs.metrics import DocumentationMetrics

agent = DocumentationGeneratorAgent()
metrics_tracker = DocumentationMetrics()

# Generate documentation
agent.run_generation_workflow('./devflow', './docs', ['api'])

# Calculate metrics
report = metrics_tracker.generate_report('./devflow')
metrics_tracker.print_report(report)
"
```

## Related Skills
- Dev Story (generates code that needs documentation)
- Code Review (validates documentation quality)
- QA Tester (verifies documentation accuracy)

## Best Practices

1. **Run Incrementally**: Use incremental updates for large codebases to save time
2. **Generate Metrics**: Always generate metrics to track documentation coverage
3. **Review Tasks**: Review proposed documentation tasks before implementing
4. **Version Control**: Commit generated documentation with code changes
5. **Customize Output**: Adjust generator settings for project-specific needs
6. **Validate Early**: Run validation phase before publishing documentation
7. **Monitor Trends**: Track metrics trends to improve documentation over time
8. **Automate**: Integrate into CI/CD pipeline for continuous documentation updates

## Anti-Patterns to Avoid

1. **Ignoring Gaps**: Don't ignore documentation gaps detected by the analyzer
2. **Manual Edits to Generated Files**: Avoid editing generated docs directly (customize generator instead)
3. **Skipping Validation**: Never skip validation phase - catch errors early
4. **Forcing Full Regeneration**: Don't use force_update unless necessary (inefficient)
5. **Neglecting Metrics**: Don't ignore metrics reports - they indicate documentation health
6. **Hardcoding Paths**: Use relative paths and configuration files for portability
7. **Documentation Drift**: Don't let documentation get out of sync with code
8. **Incomplete Coverage**: Don't accept low coverage scores - aim for ≥80%

## Advanced Usage

### Custom Documentation Templates
```python
# Customize generator output format
from devflow.docs.generator import DocumentationGenerator

generator = DocumentationGenerator()
generator.set_template('api', 'custom-api-template.md')
generator.set_template('readme', 'custom-readme-template.md')
```

### Filtering by File Patterns
```python
# Only document specific modules
agent = DocumentationGeneratorAgent()
result = agent.run_generation_workflow(
    source_path='./devflow',
    output_path='./docs',
    doc_types=['api'],
    file_patterns=['**/core/**/*.py', '**/utils/**/*.py']
)
```

### Integration with CI/CD
```bash
# Add to CI pipeline
- name: Generate Documentation
  run: |
    python -c "
    from agents.doc_generator import DocumentationGeneratorAgent
    agent = DocumentationGeneratorAgent()
    result = agent.run_generation_workflow('./src', './docs', ['api'])
    exit(0 if result.success else 1)
    "

- name: Check Documentation Coverage
  run: |
    python -c "
    from devflow.docs.metrics import DocumentationMetrics
    m = DocumentationMetrics()
    report = m.generate_report('./src')
    coverage = report.overall_coverage.percentage
    exit(0 if coverage >= 80 else 1)
    "
```

### Batch Documentation Tasks
```python
# Generate tasks for multiple projects
projects = ['./project1', './project2', './project3']

for project in projects:
    agent = DocumentationGeneratorAgent(project)
    tasks = agent.propose_documentation_tasks(project)
    # Save tasks for review and implementation
```
