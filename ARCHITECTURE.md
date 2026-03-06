# Autonomous AI Development System - Architecture

## System Overview

This system combines OpenClaw (orchestration), BMad Method (structured workflows), Taskmaster AI (task management), and OpenAI's Harness patterns to create a fully autonomous software development pipeline.

## Core Principles

1. **Humans Steer. Agents Execute.**
   - Humans design environments and specify intent
   - Agents implement, test, and deploy
   - Feedback loops ensure quality

2. **Context as a Scarce Resource**
   - AGENTS.md is a map/table of contents (~100 lines)
   - Structured docs/ directory as system of record
   - Progressive disclosure: agents discover context as needed

3. **Mechanical Enforcement Over Micromanagement**
   - Custom linters enforce architectural rules
   - Structural tests validate layer compliance
   - Automated quality gates

4. **Plans as First-Class Artifacts**
   - All plans versioned in repository
   - Execution plans with progress tracking
   - Decision logs recorded

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                            │
│  • OpenClaw Main Session                                          │
│  • Spawns and coordinates sub-agents                             │
│  • Manages HALT conditions and recovery                          │
│  • Tracks sprint status across all agents                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Skills Layer                                  │
│  ┌─────────────┬─────────────┬─────────────┬──────────────┐     │
│  │ Planning    │ Development │ Quality     │ Deployment   │     │
│  │ Skills      │ Skills      │ Skills      │ Skills       │     │
│  └─────────────┴─────────────┴─────────────┴──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Layer                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ BMad Workflows (12-agent AI dev team)                    │   │
│  │ • Product Owner → Brief                                  │   │
│  │ • Business Analyst → PRD                                 │   │
│  │ • Architect → Architecture Doc                          │   │
│  │ • UX Designer → UX Spec                                 │   │
│  │ • Scrum Master → Epics & Stories                        │   │
│  │ • Readiness Check → GO/NO-GO                             │   │
│  │ • Create Story → Story File                             │   │
│  │ • Dev Story → Implementation + Tests                    │   │
│  │ • Code Review → Adversarial Review                      │   │
│  │ • UX Review → UX Compliance                             │   │
│  │ • QA Tester → Test Execution                            │   │
│  │ • Retrospective → Learnings                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Execution Layer                         │
│  ┌─────────────┬─────────────┬─────────────┬──────────────┐     │
│  │ Claude Code │ Codex       │ Custom      │ Specialized  │     │
│  │ Agent       │ Agent       │ Agents      │ Agents       │     │
│  └─────────────┴─────────────┴─────────────┴──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure                                │
│  • tmux sessions for background execution                        │
│  • Git worktrees for isolated testing                            │
│  • Observability stack (logs, metrics, traces)                   │
│  • Custom linters for architectural enforcement                  │
│  • Taskmaster AI for task tracking                               │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
devflow/
├── .openclaw/
│   ├── workspace/
│   │   └── [project worktrees]
│   └── agents/
│       └── [agent definitions]
├── skills/
│   ├── planning/
│   │   ├── product-owner-skill.md
│   │   ├── business-analyst-skill.md
│   │   ├── architect-skill.md
│   │   ├── ux-designer-skill.md
│   │   └── scrum-master-skill.md
│   ├── development/
│   │   ├── create-story-skill.md
│   │   ├── dev-story-skill.md
│   │   └── test-skill.md
│   ├── quality/
│   │   ├── code-review-skill.md
│   │   ├── ux-review-skill.md
│   │   └── qa-tester-skill.md
│   └── deployment/
│       ├── ci-cd-skill.md
│       └── monitoring-skill.md
├── workflows/
│   ├── bmad-adapted/
│   │   ├── planning-phase.workflow
│   │   └── execution-phase.workflow
│   └── custom/
│       └── autonomous-development.workflow
├── tools/
│   ├── tmux-manager/
│   │   ├── spawn-session.sh
│   │   └── monitor-sessions.sh
│   ├── git-worktree-manager/
│   │   ├── create-worktree.sh
│   │   └── cleanup-worktrees.sh
│   └── observability/
│       ├── setup-local-stack.sh
│       └── query-logs.sh
├── docs/
│   ├── architecture/
│   │   └── system-design.md
│   ├── guides/
│   │   ├── getting-started.md
│   │   └── running-autonomous-dev.md
│   └── agentry/
│       └── AGENTS.md
├── templates/
│   ├── project-init/
│   │   └── project-template.yaml
│   └── agent-prompts/
│       └── prompt-templates.md
└── .taskmaster/
    ├── docs/
    │   └── prd.md
    └── tasks/
        └── tasks.json
```

## Key Components

### 1. Orchestrator (OpenClaw Main Session)
- Spawns isolated sub-agents via `sessions_spawn`
- Manages agent lifecycle and HALT protocol
- Coordinates multi-agent workflows
- Tracks sprint status and progress

### 2. Skills System
Each skill encapsulates a specific capability:
- **Planning Skills**: Requirements analysis, architecture design, UX specification
- **Development Skills**: Coding, testing, refactoring
- **Quality Skills**: Review, linting, validation
- **Deployment Skills**: CI/CD, monitoring

### 3. BMad Workflows Adapted for OpenClaw
Convert BMad's 12-agent workflow to OpenClaw skills:
- Each agent runs as isolated sub-agent
- State persisted in files (not memory)
- HALT protocol for blocked conditions
- Orchestrator respawns failed agents

### 4. Taskmaster Integration
- Bidirectional sync between BMad stories and Taskmaster
- Dependency management
- Progress tracking and reporting
- Status: backlog → in-progress → done

### 5. Infrastructure Tools
- **tmux-manager**: Create, monitor, cleanup background sessions
- **git-worktree-manager**: Isolated testing environments
- **observability**: Local logs, metrics, traces stack

### 6. Quality & Safety
- Custom linters for architectural enforcement
- Structural tests for layer compliance
- Automated quality gates
- Technical debt detection and cleanup

## Workflow Example

### Planning Phase
1. **Product Owner Agent** → Product Brief
2. **Business Analyst Agent** → PRD with user journeys
3. **Architect Agent** → Architecture document
4. **UX Designer Agent** → UX specifications
5. **Scrum Master Agent** → Epics & Stories with AC
6. **Readiness Check Agent** → GO/NO-GO decision

### Execution Phase (per story)
1. **Create Story Agent** → Story file with tasks
2. **Dev Story Agent** → Implementation + tests (red-green-refactor)
3. **Code Review Agent** → Adversarial review (3-10 issues)
4. **UX Review Agent** → UX compliance check
5. **QA Tester Agent** → Test execution and validation
6. **Retrospective Agent** → Sprint learnings

## Technical Stack

**Orchestration:**
- OpenClaw (agent spawning and coordination)

**AI Agents:**
- Claude Code (primary development agent)
- OpenAI Codex (secondary support)
- Custom agents for specialized tasks

**Task Management:**
- Taskmaster AI (task tracking and dependencies)

**Infrastructure:**
- tmux (session management)
- Git worktrees (isolated testing)
- Docker (containerization)
- Prometheus/Grafana (observability)

**Quality Tools:**
- ESLint (linting)
- Jest (testing)
- Custom linters (architectural rules)

## Next Steps

1. Set up repository structure
2. Create AGENTS.md with progressive disclosure
3. Implement first BMad workflow (Product Owner)
4. Create tmux-manager tool
5. Test single-agent autonomy
6. Incrementally add complexity

## Open Questions

1. How to handle agent-to-agent communication efficiently?
2. What's the optimal agent team size and composition?
3. How to balance autonomy with safety?
4. How to handle ambiguous requirements?
5. How to scale to enterprise codebases?
