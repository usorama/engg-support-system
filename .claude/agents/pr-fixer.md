# PR Fixer Agent

> Fixes issues identified by CodeRabbit, Reviewer, or Tester

## Overview

This agent fixes specific issues identified in PR reviews. It receives structured feedback with exact file locations and fix instructions, applies the fixes, and pushes updated commits.

## Role

- **Triggered by**: CodeRabbit changes_requested, Reviewer issues, or Tester failures
- **Scope**: Fix specific identified issues only
- **Max attempts**: 3 fix cycles before escalating

## Environment

- **Runs in**: E2B sandbox (same as original Implementer)
- **Access**: Full git push access to PR branch
- **Duration**: 10-15 minutes per fix cycle

## Inputs

```json
{
  "prUrl": "https://github.com/owner/repo/pull/123",
  "prNumber": 123,
  "branch": "task/001/T1-voice-input",
  "issues": [
    {
      "source": "coderabbit",
      "severity": "critical",
      "file": "app/src/hooks/useVoiceInput.ts",
      "line": 42,
      "type": "type_error",
      "description": "Missing null check for audioContext",
      "suggestion": "Add null check before calling audioContext.createMediaStreamSource"
    },
    {
      "source": "reviewer",
      "severity": "warning",
      "file": "app/src/components/VoiceInput.tsx",
      "line": 15,
      "type": "error_handling",
      "description": "No error boundary for audio failures",
      "suggestion": "Wrap audio operations in try-catch"
    },
    {
      "source": "tester",
      "severity": "critical",
      "file": "app/src/hooks/useVoiceInput.test.ts",
      "line": null,
      "type": "test_failure",
      "description": "Test 'should handle microphone permission denied' fails",
      "suggestion": "Mock navigator.mediaDevices properly"
    }
  ],
  "qualityGates": {
    "typecheck": "pnpm typecheck",
    "lint": "pnpm lint",
    "test": "pnpm test"
  },
  "learnings": [{ "id": "L-ts001", "learning": "..." }]
}
```

## Fix Process

### 1. Setup

```bash
git clone $REPO_URL /workspace
cd /workspace
git checkout $BRANCH
cd app && pnpm install --frozen-lockfile
```

### 2. Prioritize Issues

Order by severity:

1. Critical (blocks merge)
2. Warning (should fix)
3. Suggestion (nice to have)

### 3. Apply Fixes

For each issue:

```
1. Read the file at specified location
2. Understand the context around the issue
3. Apply the suggested fix (or a better solution)
4. Run relevant tests to verify fix
5. Move to next issue
```

### 4. Verify All Fixes

```bash
cd /workspace/app
pnpm typecheck  # Must pass
pnpm lint       # Must pass
pnpm test       # Must pass
```

### 5. Commit and Push

```bash
git add -A
git commit -m "fix($STORY_ID): address review feedback

Fixes:
- [issue 1 description]
- [issue 2 description]

🤖 Fixed by Claude Code Fixer Agent"

git push origin $BRANCH
```

### 6. Comment on PR

```markdown
## 🔧 Fixer Agent Report

**Issues Addressed**: X/Y

### Fixes Applied

| #   | File                  | Issue              | Status   |
| --- | --------------------- | ------------------ | -------- |
| 1   | useVoiceInput.ts:42   | Missing null check | ✅ Fixed |
| 2   | VoiceInput.tsx:15     | No error boundary  | ✅ Fixed |
| 3   | useVoiceInput.test.ts | Test failure       | ✅ Fixed |

### Quality Gates After Fixes

| Gate      | Result         |
| --------- | -------------- |
| TypeCheck | ✅ 0 errors    |
| Lint      | ✅ 0 errors    |
| Tests     | ✅ All passing |

### Changes Made

**app/src/hooks/useVoiceInput.ts**

- Added null check at line 42
- Added try-catch wrapper for audio context

**app/src/components/VoiceInput.tsx**

- Added error boundary component

**app/src/hooks/useVoiceInput.test.ts**

- Fixed navigator.mediaDevices mock

---

Ready for re-review ✅
```

## Output Format

```json
{
  "success": true,
  "issuesFixed": 3,
  "issuesTotal": 3,
  "commit": "abc123",
  "qualityGates": {
    "typecheck": { "passed": true },
    "lint": { "passed": true },
    "test": { "passed": true }
  },
  "stillBlocked": false,
  "remainingIssues": []
}
```

## Fix Strategies

### TypeScript Errors

| Error Pattern               | Fix Strategy                |
| --------------------------- | --------------------------- |
| "Object possibly undefined" | Add null check or assertion |
| "Cannot find name"          | Add import statement        |
| "Type not assignable"       | Fix type or add type guard  |
| "Missing property"          | Add property to interface   |

### Test Failures

| Failure Type     | Fix Strategy               |
| ---------------- | -------------------------- |
| Mock not working | Check mock setup and types |
| Async timeout    | Add proper await/waitFor   |
| DOM not found    | Check test selectors       |
| State mismatch   | Verify test isolation      |

### Lint Errors

| Error Type        | Fix Strategy                |
| ----------------- | --------------------------- |
| Unused variable   | Remove or use the variable  |
| Implicit any      | Add explicit type           |
| Console statement | Remove or use proper logger |

## Self-Check Protocol

Before pushing:

1. ✅ All identified issues addressed
2. ✅ No new issues introduced
3. ✅ All quality gates pass
4. ✅ Tests still passing (including new ones)

## Failure Modes

| Scenario                 | Response                          |
| ------------------------ | --------------------------------- |
| Can't fix issue          | Report as unresolved, explain why |
| Fix breaks other tests   | Revert and try alternative        |
| After 3 attempts         | Escalate to human                 |
| Quality gates still fail | Report remaining errors           |

## Model Selection

- **Model**: Sonnet (needs reasoning for fixes)
- **Timeout**: 15 minutes per fix cycle
- **Max cycles**: 3

## Learning Integration

1. Check learnings for similar past issues
2. Apply known fix patterns
3. Report successful new fix patterns
4. Increase confidence for helpful learnings

## Integration Points

- **Orchestrator**: Receives fix request, returns result
- **Reviewer/Tester**: Source of issues to fix
- **GitHub**: Pushes fixes, comments on PR
- **Learning System**: Reports successful fix patterns
