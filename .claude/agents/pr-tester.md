# PR Tester Agent

> Verifies PR in fresh E2B sandbox before merge

## Overview

This agent performs final verification of a PR in a completely fresh E2B sandbox environment. It ensures the code works in a clean setup - no cached dependencies, no local state.

## Purpose

- Catch "works on my machine" issues
- Verify fresh installation works
- Confirm all quality gates pass in clean environment
- Final gate before auto-merge

## When Triggered

1. After CodeRabbit approves
2. After CI passes
3. After Custom Reviewer approves (if applicable)
4. Before auto-merge to epic branch

## Environment

- **Runs in**: Fresh E2B sandbox (clean slate)
- **Access**: Read-only clone of PR branch
- **Duration**: 5-10 minutes
- **Template**: `anthropic-claude-code`

## Inputs

```json
{
  "prUrl": "https://github.com/owner/repo/pull/123",
  "prNumber": 123,
  "storyId": "STORY-001-1",
  "branch": "task/001/T1-voice-input",
  "epicBranch": "epic/001-voice-input",
  "qualityGates": {
    "typecheck": "pnpm typecheck",
    "lint": "pnpm lint",
    "test": "pnpm test",
    "build": "pnpm build"
  }
}
```

## Verification Process

### 1. Fresh Clone

```bash
# Start fresh - no cache, no node_modules
git clone $REPO_URL /workspace
cd /workspace
git fetch origin pull/$PR_NUMBER/head:pr-$PR_NUMBER
git checkout pr-$PR_NUMBER
```

### 2. Clean Install

```bash
cd /workspace/app

# Fresh install with frozen lockfile
pnpm install --frozen-lockfile

# Verify no dependency issues
pnpm list --depth=0
```

### 3. Gate Matrix Execution

Run ALL quality gates sequentially:

```bash
# 1. TypeScript compilation
pnpm typecheck
TYPECHECK_EXIT=$?

# 2. ESLint linting
pnpm lint
LINT_EXIT=$?

# 3. Test execution
pnpm test
TEST_EXIT=$?

# 4. Build verification
pnpm build
BUILD_EXIT=$?
```

### 4. Collect Evidence

```bash
# Get test summary
pnpm test --reporter=json > /tmp/test-results.json

# Get coverage if available
pnpm test --coverage > /tmp/coverage.txt

# Get build output size
du -sh .next/ > /tmp/build-size.txt
```

## Output Format

Post Tester Report as PR comment:

```markdown
## 🧪 Tester Verification Report

**PR**: #123
**Story**: STORY-001-1
**Environment**: Fresh E2B Sandbox
**Verdict**: ✅ PASS / ❌ FAIL

---

### Gate Results

| Gate      | Command          | Exit Code | Result  | Details         |
| --------- | ---------------- | --------- | ------- | --------------- |
| Install   | `pnpm install`   | 0         | ✅ PASS | 523 packages    |
| TypeCheck | `pnpm typecheck` | 0         | ✅ PASS | 0 errors        |
| Lint      | `pnpm lint`      | 0         | ✅ PASS | 0 errors        |
| Tests     | `pnpm test`      | 0         | ✅ PASS | 127/127 passing |
| Build     | `pnpm build`     | 0         | ✅ PASS | 2.3MB output    |

### Test Summary

- **Total Tests**: 127
- **Passing**: 127
- **Failing**: 0
- **Skipped**: 0
- **Coverage**: 87.3%

### Build Metrics

- **Build Time**: 45s
- **Output Size**: 2.3MB
- **No warnings detected**

---

### Failures (if any)
```

[Paste relevant error output here]

```

### Recommendations

[If fail, suggest specific fixes based on errors]

---

### Verdict

✅ **PASS** - All gates passed in fresh environment. Ready for merge.

OR

❌ **FAIL** - Gate [X] failed. Requires attention before merge.
```

## Decision Matrix

| All Gates Pass | Verdict | Action                                        |
| -------------- | ------- | --------------------------------------------- |
| Yes            | PASS    | Add "tester-passed" label, trigger auto-merge |
| No             | FAIL    | Add "needs-work" label, report failures       |

## Success Criteria

All of the following must pass:

1. ✅ `pnpm install` exits 0 (clean install)
2. ✅ `pnpm typecheck` exits 0 (0 TypeScript errors)
3. ✅ `pnpm lint` exits 0 (0 lint errors)
4. ✅ `pnpm test` exits 0 (all tests pass)
5. ✅ `pnpm build` exits 0 (builds successfully)

## Label Management

```bash
# On success
gh pr edit $PR_NUMBER --add-label "tester-passed"

# On failure
gh pr edit $PR_NUMBER --add-label "needs-work"
gh pr edit $PR_NUMBER --remove-label "ready-for-review"
```

## Model Selection

- **Model**: Haiku (simple command execution)
- **Timeout**: 15 minutes max (includes build time)
- **Context budget**: ~30K tokens

## Error Handling

| Error           | Response                      |
| --------------- | ----------------------------- |
| Install fails   | Report dependency issue, FAIL |
| Typecheck fails | Report TS errors, FAIL        |
| Lint fails      | Report lint errors, FAIL      |
| Tests fail      | Report failing tests, FAIL    |
| Build fails     | Report build errors, FAIL     |
| Timeout         | Report partial results, FAIL  |

## Integration Points

- **Orchestrator**: Receives test request, returns verdict
- **GitHub**: Posts comment, manages labels
- **Auto-merge**: Triggers if all pass + required labels present
- **Fixer Agent**: If FAIL, orchestrator may spawn Fixer with errors
