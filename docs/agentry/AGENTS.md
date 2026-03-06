# AGENTS.md - Autonomous AI Development System

## Project Overview
This is an autonomous AI development system built with OpenClaw, BMad Method, and Taskmaster AI.

**Core Philosophy**: Humans steer. Agents execute.

## Quick Navigation

### For All Agents
- **Getting Started**: docs/guides/getting-started.md
- **Architecture**: docs/architecture/system-design.md
- **Task Status**: Run `taskmaster list` or check `.taskmaster/tasks/tasks.json`

### For Planning Agents
- **Product Owner**: skills/planning/product-owner-skill.md
- **Business Analyst**: skills/planning/business-analyst-skill.md
- **Architect**: skills/planning/architect-skill.md
- **UX Designer**: skills/planning/ux-designer-skill.md
- **Scrum Master**: skills/planning/scrum-master-skill.md

### For Execution Agents
- **Create Story**: skills/development/create-story-skill.md
- **Dev Story**: skills/development/dev-story-skill.md
- **Code Review**: skills/quality/code-review-skill.md
- **UX Review**: skills/quality/ux-review-skill.md
- **QA Tester**: skills/quality/qa-tester-skill.md

### For Deployment
- **CI/CD**: skills/deployment/ci-cd-skill.md
- **Monitoring**: skills/deployment/monitoring-skill.md

## Agent Coordination

### BMad Workflow Order
1. Product Owner → Brief
2. Business Analyst → PRD
3. Architect → Architecture
4. UX Designer → UX Spec
5. Scrum Master → Epics & Stories
6. Readiness Check → GO/NO-GO
7. For each story: Create Story → Dev Story → Code Review → [UX Review] → [QA Tester]
8. Retrospective → Learnings

### HALT Protocol
When an agent cannot proceed, return:
```
HALT: [reason] | Context: [what's needed]
```

The orchestrator will:
- Resolve and respawn
- Ask the user (for ambiguous decisions)
- Mark blocked (log and continue)

## Quality Standards

### Code Quality
- All code must pass ESLint
- All tests must pass (Jest)
- Coverage threshold: 80%

### Architectural Rules
- Follow layered architecture: Types → Config → Repo → Service → Runtime → UI
- No backward dependencies
- Use custom linters to enforce

### Documentation Standards
- All plans are versioned in repository
- Design decisions are recorded in docs/decisions/
- API documentation is auto-generated from code

## Tools Available

### Background Execution
- `tools/tmux-manager/spawn-session.sh` - Spawn new tmux session
- `tools/tmux-manager/monitor-sessions.sh` - Monitor active sessions

### Git Worktrees
- `tools/git-worktree-manager/create-worktree.sh` - Create isolated worktree
- `tools/git-worktree-manager/cleanup-worktrees.sh` - Cleanup old worktrees

### Observability
- `tools/observability/setup-local-stack.sh` - Setup local monitoring
- `tools/observability/query-logs.sh` - Query application logs

## Context Management Principles

### Progressive Disclosure
- Start with small, stable entry point (this file)
- Agents discover context as needed
- Don't overwhelm with upfront instructions

### Mechanical Verification
- Linters validate documentation freshness
- CI checks for cross-links
- Automated tests verify code matches docs

### Knowledge Location
- Repository-local, versioned artifacts only
- No external dependencies (Slack, Google Docs)
- If it's not in the repo, it doesn't exist to agents

## Working with Taskmaster AI

### Task States
- `backlog` - Not yet started
- `in-progress` - Currently being worked
- `done` - Completed

### Task Dependencies
Tasks can have dependencies. Use:
```bash
taskmaster show <task-id>  # View dependencies
taskmaster move --from=<task-id> --from-tag=backlog --to-tag=in-progress  # Move with dependencies
```

### Research Capabilities
Taskmaster can research fresh information:
```bash
taskmaster research "Latest best practices for JWT authentication"
```

## Common Workflows

### Starting a New Project
1. Run Product Owner skill to generate brief
2. Run Business Analyst skill to create PRD
3. Run Architect skill to design system
4. Run UX Designer skill for specifications
5. Run Scrum Master skill to break down stories
6. Run Readiness Check skill for GO/NO-GO

### Implementing a Story
1. Run Create Story skill
2. Run Dev Story skill (red-green-refactor)
3. Run Code Review skill
4. Run UX Review skill (if applicable)
5. Run QA Tester skill
6. Mark task as done in Taskmaster

### Handling Failures
1. Check HALT condition context
2. Resolve missing information
3. Respawn agent with updated context
4. Update documentation if needed

## Performance Patterns

### For Long-Running Tasks
- Use tmux sessions for isolation
- Monitor with `tools/tmux-manager/monitor-sessions.sh`
- Check logs periodically

### For Parallel Work
- Spawn multiple agents simultaneously
- Use git worktrees for isolation
- Aggregate results at the end

### For Quality Assurance
- Always run adversarial code review
- Use automated testing
- Validate against acceptance criteria
