# Codex Worker SKILL

## Skill Name
Codex Worker Agent

## Description
This skill enables OpenClaw to spawn OpenAI Codex as an isolated worker agent for code generation, implementation, and file manipulation tasks. Codex serves as an alternative worker agent in the DevFlow Auto-Dev system, executing specific coding tasks assigned by the orchestrator and returning results through file-based state management. Powered by OpenAI's GPT-4 class models, Codex provides complementary capabilities to Claude Code for diverse coding tasks.

**When to use this skill:**
- Implementing new features from specifications
- Refactoring existing code
- Writing unit tests
- Fixing bugs with clear reproduction steps
- Code review and analysis
- Documentation generation
- Tasks requiring OpenAI model capabilities

## Prerequisites

### Required Dependencies
- Node.js 22+ (for OpenClaw)
- Codex CLI (`codex` command available in PATH via `@openai/codex`)
- Valid `OPENAI_API_KEY` environment variable
- Write access to `~/.openclaw/state/` directory

### Environment Variables
```bash
OPENAI_API_KEY=sk-...                  # Required: OpenAI API key
CODEX_MODEL=o4-mini                    # Optional: Model selection (o4-mini, o3, gpt-4.1)
CODEX_MAX_TOKENS=8192                  # Optional: Max output tokens
CODEX_TEMPERATURE=0.7                  # Optional: Temperature for generation
```

### Directory Structure
```
~/.openclaw/
├── state/
│   ├── workers/
│   │   └── codex-{id}.json            # Worker state files
│   └── output/
│       └── codex-{id}.json            # Worker output files
└── context/
    └── tasks/
        └── {task-id}.json             # Task context files
```

## Usage

### Basic Invocation via OpenClaw

```json5
{
  "skill": "codex",
  "action": "spawn",
  "params": {
    "task_type": "implement-feature",
    "context_file": "~/.openclaw/context/tasks/feature-001.json",
    "output_file": "~/.openclaw/state/output/codex-001.json",
    "timeout": 300000,
    "isolation": true
  }
}
```

### sessions_spawn Pattern

OpenClaw spawns Codex workers using the `sessions_spawn` protocol:

```json5
{
  "skill": "spawn-worker",
  "params": {
    "agent_type": "codex",
    "task": "implement-feature",
    "context_file": ".openclaw/context/feature-001.json",
    "output_file": ".openclaw/output/feature-001.json",
    "timeout": 300000,
    "spawn_children": false  // Workers cannot spawn children by default
  }
}
```

### Command-Line Invocation

```bash
# Direct Codex invocation for testing
codex --print "Implement the feature described in spec.md" \
  --context-file ~/.openclaw/context/tasks/feature-001.json

# With specific model
codex --model o4-mini \
  --max-tokens 8192 \
  "Review and refactor src/handlers/auth.ts"

# Full approval mode (use with caution)
codex --full-auto "Implement user authentication"
```

## Implementation

### Worker Lifecycle

1. **Spawn Phase**
   - OpenClaw creates context file with task specification
   - Worker process is spawned with isolated environment
   - State file is initialized with "running" status

2. **Execution Phase**
   - Worker reads context file for task details
   - Executes Codex CLI with appropriate prompts
   - Writes progress updates to state file

3. **Completion Phase**
   - Worker writes results to output file
   - State file updated to "completed" status
   - Orchestrator notified via file polling

4. **HALT Protocol** (when blocked)
   ```yaml
   when: worker_blocked_or_needs_input
   actions:
     - write_state_to_file: ~/.openclaw/state/workers/codex-{id}.json
     - notify_orchestrator: true
     - wait_for: human_input OR timeout
     - resume_from: last_checkpoint
   ```

### Context File Format

```json
{
  "task_id": "feature-001",
  "task_type": "implement-feature",
  "spec_file": "specs/feature-001/spec.md",
  "files_to_modify": ["src/handlers/auth.ts"],
  "files_to_create": ["tests/auth.test.ts"],
  "constraints": {
    "follow_existing_patterns": true,
    "max_changes": 500,
    "require_tests": true
  },
  "context": {
    "related_files": ["src/types/auth.ts", "src/utils/jwt.ts"],
    "existing_patterns": ["src/handlers/user.ts"]
  }
}
```

### Output File Format

```json
{
  "task_id": "feature-001",
  "status": "completed",
  "files_modified": ["src/handlers/auth.ts"],
  "files_created": ["tests/auth.test.ts"],
  "summary": "Implemented JWT authentication with refresh token support",
  "changes": [
    {
      "file": "src/handlers/auth.ts",
      "action": "modified",
      "lines_added": 45,
      "lines_removed": 12
    }
  ],
  "test_results": {
    "passed": 8,
    "failed": 0,
    "coverage": "94.2%"
  },
  "notes": "All acceptance criteria met"
}
```

### Isolation Constraints

Spawned Codex workers operate under these constraints:
- Cannot spawn further child agents without explicit permission
- File system access limited to project directory
- Network access controlled by environment configuration
- Memory and CPU limits enforced by orchestrator

## Expected Output

### Successful Execution
```json
{
  "status": "completed",
  "exit_code": 0,
  "files_modified": ["list", "of", "files"],
  "files_created": ["list", "of", "new", "files"],
  "summary": "Human-readable summary of changes",
  "verification": {
    "tests_passed": true,
    "lint_passed": true,
    "build_passed": true
  }
}
```

### Blocked Execution (HALT)
```json
{
  "status": "halted",
  "reason": "needs_clarification",
  "checkpoint": "phase-2-implementation",
  "question": "Should the auth handler support OAuth2 in addition to JWT?",
  "options": ["jwt_only", "oauth2_only", "both"],
  "state_file": "~/.openclaw/state/workers/codex-001.json"
}
```

### Failed Execution
```json
{
  "status": "failed",
  "exit_code": 1,
  "error": {
    "type": "implementation_error",
    "message": "Unable to parse spec.md: missing required section",
    "file": "specs/feature-001/spec.md",
    "line": 42
  },
  "partial_results": {
    "files_modified": ["src/handlers/auth.ts"],
    "last_successful_step": "created_auth_handler"
  }
}
```

## Error Handling

### Error Categories

| Category | Handling Strategy |
|----------|-------------------|
| `api_error` | Retry with exponential backoff (max 3 retries) |
| `timeout_error` | Save checkpoint, notify orchestrator, await resume |
| `parse_error` | Report error details, request clarification |
| `file_error` | Log error, attempt recovery, report if unrecoverable |
| `constraint_violation` | Rollback changes, report violation details |
| `rate_limit_error` | Wait and retry with exponential backoff |

### Retry Configuration

```yaml
retry_policy:
  max_retries: 3
  initial_delay: 1000  # ms
  max_delay: 60000     # ms (OpenAI rate limits can be longer)
  multiplier: 2
  retryable_errors:
    - api_error
    - timeout_error
    - rate_limit_error
    - network_error
```

### Crash Recovery

1. On crash, worker writes current state to checkpoint file
2. Orchestrator detects crash via process monitoring
3. Orchestrator reads checkpoint and determines resume point
4. New worker spawned with `resume_from` parameter
5. Worker continues from last successful checkpoint

```bash
# Recovery command
codex --resume ~/.openclaw/state/workers/codex-001-checkpoint.json
```

## Integration with Other Skills

### Depends On
- **taskmaster**: For task context and priority
- **spec-driven**: For specification parsing

### Used By
- **bmad**: During development phase (dev-story agent)
- **spec-driven**: During implementation phase

### Communication Pattern
```
┌─────────────┐     context.json      ┌─────────────┐
│  TaskMaster │ ───────────────────▶ │   Codex     │
└─────────────┘                       │   Worker    │
                                      └──────┬──────┘
                                             │
┌─────────────┐     output.json             │
│   BMAD      │ ◀───────────────────────────┘
│ Orchestrator│
└─────────────┘
```

## Examples

### Example 1: Implement Feature

```bash
# Context file: ~/.openclaw/context/tasks/feat-auth.json
codex-worker \
  --context ~/.openclaw/context/tasks/feat-auth.json \
  --output ~/.openclaw/state/output/codex-auth.json \
  --timeout 300000
```

### Example 2: Fix Bug

```json5
{
  "skill": "codex",
  "action": "spawn",
  "params": {
    "task_type": "fix-bug",
    "bug_report": "TypeError in auth.ts line 42",
    "files_to_modify": ["src/handlers/auth.ts"],
    "require_test": true,
    "timeout": 180000
  }
}
```

### Example 3: Code Review

```json5
{
  "skill": "codex",
  "action": "spawn",
  "params": {
    "task_type": "code-review",
    "target_files": ["src/handlers/auth.ts"],
    "review_checklist": [
      "security",
      "performance",
      "maintainability",
      "test_coverage"
    ],
    "output_format": "markdown"
  }
}
```

## Model Selection Guide

| Model | Best For | Notes |
|-------|----------|-------|
| `o4-mini` | Fast coding tasks, iteration | Default, good balance of speed/quality |
| `o3` | Complex reasoning, architecture | Higher capability, slower |
| `gpt-4.1` | General purpose coding | Legacy option, still capable |

## Security Considerations

1. **API Key Protection**: Never log or write API keys to files
2. **File Permissions**: State files chmod 600 (user-readable only)
3. **Input Sanitization**: All inputs validated before processing
4. **Sandboxed Execution**: Workers operate in isolated contexts
5. **Audit Trail**: All actions logged to `~/.openclaw/logs/codex/`
6. **Approval Mode**: Use `--full-auto` only in trusted environments

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-07 | Initial skill definition for DevFlow Auto-Dev |
