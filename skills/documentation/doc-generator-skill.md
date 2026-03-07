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
# Set up the documentation generator agent
from agents.doc_generator import DocumentationGeneratorAgent

agent = DocumentationGeneratorAgent(project_path="/path/to/project")
```

### 2. Analyze Codebase
```bash
# Analyze code structure and extract documentation information
request = DocGenerationRequest(
    source_path="./devflow",
    output_path="./docs",
    doc_types=["api", "readme", "architecture"],
    force_update=False,
    generate_metrics=True
)

# Run analysis phase
analysis_result = agent.analyze_codebase(request.source_path)
print(f"Found {len(analysis_result.get('files', []))} files to analyze")
```

### 3. Detect Documentation Gaps
```bash
# Compare code state with existing documentation
gaps = agent.detect_documentation_gaps(request.source_path)

for gap in gaps:
    print(f"Gap: {gap['type']} - {gap['file_path']}")
    print(f"  Reason: {gap['reason']}")
```

### 4. Generate Documentation
```bash
# Generate documentation for requested types
result = agent.run_generation_workflow(request)

if result.success:
    print(f"Generated {len(result.files_generated)} documentation files")
    print(f"Duration: {result.duration:.2f}s")
else:
    print(f"Errors: {result.errors}")
```

### 5. Validate and Update Metrics
```bash
# Validate generated documentation
validation_result = agent._validate_phase(result)

# Calculate metrics
if request.generate_metrics:
    metrics = agent._calculate_metrics(result)
    print(f"Coverage: {metrics.get('coverage', 'N/A')}")
    print(f"Quality Score: {metrics.get('quality_score', 'N/A')}")
```

### 6. Propose Documentation Tasks (Optional)
```bash
# Create tasks for missing or outdated documentation
tasks = agent.propose_documentation_tasks(request.source_path)

for task in tasks:
    print(f"Task {task.task_id}: {task.type}")
    print(f"  Priority: {task.priority}")
    print(f"  Action: {task.suggested_action}")
```

### 7. Incremental Updates (Ongoing)
```bash
# Update only changed files (efficient for large codebases)
incremental_result = agent.incremental_update(
    source_path=request.source_path,
    doc_types=request.doc_types
)

print(f"Updated {len(incremental_result.files_generated)} files")
print(f"Detected {incremental_result.metrics.get('changes_detected', 0)} changes")
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
