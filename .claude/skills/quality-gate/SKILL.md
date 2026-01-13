---
name: quality-gate
description: Quality verification before commits and deployments. Use for quality checks, running tests, checking coverage, validating changes.
allowed-tools: Bash, Read, Grep, Glob
---

# Quality Gate Skill

Verify code quality before commits and deployments.

## Quality Stages

### Stage 1: Static Analysis

```bash
# TypeScript check - MUST pass with 0 errors
pnpm run typecheck

# Lint check - MUST pass
pnpm run lint
```

**Failure Actions:**

- List all TypeScript errors with file:line
- Separate lint errors into auto-fixable vs manual

### Stage 2: Tests

```bash
# Run all tests
pnpm run test

# Check coverage
pnpm run test:coverage
```

**Requirements:**

- All tests must pass
- Coverage ≥ 80%

### Stage 3: Build

```bash
# Verify build succeeds
pnpm run build
```

## Output Format

### All Passing

```
✓ TypeScript: 0 errors
✓ Lint: Clean
✓ Tests: XX passed
✓ Coverage: XX%
✓ Build: Success
━━━━━━━━━━━━━━━━━━━━━━
Ready to commit!
```

### Failures

```
✗ TypeScript: X errors
  - src/file.ts:42 - Error message

✗ Tests: X failed
  - test/file.test.ts - Test name
    Expected: X
    Received: Y

━━━━━━━━━━━━━━━━━━━━━━
BLOCKED: Fix issues before commit
```

## Quality Standards

| Metric            | Minimum | Target |
| ----------------- | ------- | ------ |
| TypeScript Errors | 0       | 0      |
| Lint Errors       | 0       | 0      |
| Test Pass Rate    | 100%    | 100%   |
| Coverage          | 80%     | 90%    |
| Build             | Pass    | Pass   |
