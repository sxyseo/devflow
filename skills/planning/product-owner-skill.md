# Product Owner Skill

## Purpose
Generate a product brief from a high-level idea or request.

## When to Use
- Starting a new project
- Defining a new feature
- Clarifying product requirements

## Inputs
- Project idea or feature request
- Target audience (optional)
- Business goals (optional)

## Outputs
- Product Brief in `.taskmaster/docs/product-brief.md`

## Process

1. **Analyze the Request**
   - Identify the core problem being solved
   - Understand the target users
   - Clarify the value proposition

2. **Define Key Elements**
   - Problem statement
   - Solution overview
   - Target users
   - Key features
   - Success metrics

3. **Create Product Brief**
   Write a clear, concise brief that includes:
   ```markdown
   # Product Brief

   ## Problem Statement
   [What problem are we solving?]

   ## Solution Overview
   [High-level solution description]

   ## Target Users
   - [User persona 1]
   - [User persona 2]

   ## Key Features
   - [Feature 1]
   - [Feature 2]
   - [Feature 3]

   ## Success Metrics
   - [Metric 1]
   - [Metric 2]
   - [Metric 3]
   ```

4. **Save Brief**
   - Save to `.taskmaster/docs/product-brief.md`
   - Report completion to orchestrator

## Quality Checklist
- [ ] Brief is clear and concise (1-2 pages)
- [ ] Problem is well-defined
- [ ] Solution addresses the problem
- [ ] Success metrics are measurable
- [ ] Target users are identified

## HALT Conditions
Return HALT if:
- **Missing context**: `HALT: Need clarification on target audience | Context: Specify who will use this product`
- **Conflicting requirements**: `HALT: Requirements conflict | Context: Need to prioritize features`
- **Unclear value proposition**: `HALT: Value proposition unclear | Context: Define what makes this unique`

## Example Usage

### As an OpenClaw Skill
```
claude "Run product-owner skill. Idea: A task management app for AI developers that integrates with Claude Code and Cursor"
```

### As a Sub-Agent
```bash
./tools/tmux-manager/spawn-session.sh "product-owner" "planning" \
  "Generate product brief for: AI task management app"
```

## Related Skills
- Business Analyst (uses this brief)
- Architect (uses this brief)
- UX Designer (uses this brief)

## Next Steps
After completing this skill:
1. Run Business Analyst skill to create PRD
2. Run Architect skill to design system
3. Run UX Designer skill for specifications
