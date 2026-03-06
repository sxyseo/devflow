# Dev Story Skill

## Purpose
Implement a story following red-green-refactor methodology with full test coverage.

## When to Use
- Implementing a user story
- Creating a new feature
- Fixing a bug with tests

## Inputs
- Story file from `.taskmaster/stories/<story-id>.md`
- Architecture document (if applicable)

## Outputs
- Implementation code
- Test suite (100% coverage)
- Updated documentation

## Process

### 1. Read and Understand Story
```bash
# Read story file
cat .taskmaster/stories/<story-id>.md
```

### 2. Create Git Worktree
```bash
# Create isolated worktree for this story
./tools/git-worktree-manager/create-worktree.sh "story-<story-id>"
cd /tmp/devflow-worktrees/story-<story-id>
```

### 3. Red-Green-Refactor Cycle

#### RED: Write Failing Test
```bash
# Create test file
touch src/features/<feature-name>.test.ts
```

Write test that fails:
```typescript
describe('<Feature Name>', () => {
  it('should <expected behavior>', () => {
    // Test implementation
  });
});
```

Run test (should fail):
```bash
npm test -- src/features/<feature-name>.test.ts
```

#### GREEN: Make Test Pass
```bash
# Create implementation file
touch src/features/<feature-name>.ts
```

Write minimal code to make test pass:
```typescript
export function <featureFunction>() {
  // Implementation
}
```

Run test (should pass):
```bash
npm test -- src/features/<feature-name>.test.ts
```

#### REFACTOR: Improve Code
- Review code for improvements
- Ensure architectural compliance
- Check for edge cases
- Update documentation

### 4. Verify Quality
```bash
# Run all tests
npm test

# Run linter
npm run lint

# Check coverage
npm run test:coverage
```

### 5. Create Pull Request
```bash
# Commit changes
git add .
git commit -m "feat: implement <story-name>

- Add feature implementation
- Add comprehensive tests
- Update documentation"

# Push to remote
git push -u origin story-<story-id>

# Create PR using gh
gh pr create --title "feat: <story-name>" --body "$(cat .taskmaster/stories/<story-id>.md)"
```

## Quality Standards

### Code Quality
- [ ] All tests pass
- [ ] 100% test coverage for new code
- [ ] No ESLint warnings
- [ ] TypeScript strict mode compliant
- [ ] Follows architectural layering rules

### Test Quality
- [ ] Tests cover happy path
- [ ] Tests cover error cases
- [ ] Tests cover edge cases
- [ ] Tests are readable and maintainable
- [ ] Tests use Given/When/Then format where applicable

### Documentation
- [ ] Code is self-documenting (clear names)
- [ ] Complex logic has comments
- [ ] API documentation is updated
- [ ] README is updated if needed

## HALT Conditions

Return HALT if:
- **Missing architecture**: `HALT: Need architecture guidance | Context: Check docs/architecture/system-design.md`
- **Unclear requirements**: `HALT: Story requirements unclear | Context: Review story file and clarify acceptance criteria`
- **Missing dependencies**: `HALT: Need dependency installation | Context: Install required packages`
- **Test failure**: `HALT: Tests failing after refactor | Context: Review test output and fix implementation`

## Example Workflow

```bash
# Start implementation
./tools/tmux-manager/spawn-session.sh "dev-story-123" "development" \
  "Implement story 123: User authentication"

# Monitor progress
./tools/tmux-manager/monitor-sessions.sh

# When complete, verify
cd /tmp/devflow-worktrees/story-123
npm test
npm run lint
```

## Related Skills
- Create Story (generates story file)
- Code Review (reviews implementation)
- QA Tester (validates implementation)

## Best Practices

1. **Small Increments**: One small test-implementation cycle at a time
2. **Continuous Testing**: Run tests after every change
3. **Refactor Mercilessly**: Improve code while keeping tests green
4. **Document Decisions**: Record why you made specific choices
5. **Handle Edge Cases**: Think about error conditions and edge cases
6. **Performance Awareness**: Consider performance implications
7. **Security First**: Validate inputs and sanitize outputs

## Anti-Patterns to Avoid

1. **Writing tests after code**: Always write tests first (TDD)
2. **Skipping refactor**: Don't leave code in a messy state
3. **Ignoring failing tests**: Never commit with failing tests
4. **Over-engineering**: Keep it simple, refactor later if needed
5. **Hardcoding values**: Use configuration and constants
