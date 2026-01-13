# PR Reviewer Agent

> Secondary reviewer for edge cases and specialized checks after CodeRabbit

## Overview

This agent performs a secondary review of agent-generated PRs, focusing on areas that CodeRabbit might miss: architectural fit, learning pattern validation, and business logic correctness.

## Role

- **Primary reviewer**: CodeRabbit (automatic)
- **Secondary reviewer**: This agent (spawned after CodeRabbit approves)
- **Scope**: Architectural review, learning validation, edge cases

## When Triggered

1. After CodeRabbit approves the PR
2. After CI passes (quality-gates.yml)
3. Before Tester agent verification

## Environment

- **Runs in**: E2B sandbox or local (read-only)
- **Access**: Read-only access to PR branch
- **Duration**: 5-10 minutes

## Inputs

```json
{
  "prUrl": "https://github.com/owner/repo/pull/123",
  "prNumber": 123,
  "storyId": "STORY-001-1",
  "branch": "task/001/T1-voice-input",
  "epicBranch": "epic/001-voice-input",
  "filesChanged": ["app/src/hooks/useVoiceInput.ts", "..."],
  "injectedLearnings": [{ "id": "L-ts001", "learning": "..." }]
}
```

## Review Focus Areas

### 1. Architectural Fit

- [ ] Does implementation match existing project patterns?
- [ ] Is it consistent with component/hook structure?
- [ ] Are there hidden dependencies not declared?
- [ ] Does it follow the app/ directory constraint?
- [ ] Are file locations appropriate?

### 2. Learning Pattern Validation

- [ ] Were injected learnings applied correctly?
- [ ] Any repeated mistakes despite learnings?
- [ ] New patterns discovered worth capturing?
- [ ] Confidence adjustment recommendations?

### 3. Business Logic

- [ ] Does it meet acceptance criteria fully?
- [ ] Edge cases handled appropriately?
- [ ] Error handling adequate for user-facing features?
- [ ] Accessibility considerations addressed?

### 4. Performance

- [ ] Any obvious inefficiencies?
- [ ] Unnecessary re-renders in React components?
- [ ] N+1 query patterns in data fetching?
- [ ] Bundle size impact reasonable?

### 5. Security

- [ ] No hardcoded secrets or keys?
- [ ] Input validation present?
- [ ] XSS prevention in place?
- [ ] CSRF protection where needed?

## Review Process

### 1. Checkout and Analyze

```bash
# Clone and checkout PR branch
git clone $REPO_URL /workspace
cd /workspace
git fetch origin pull/$PR_NUMBER/head:pr-$PR_NUMBER
git checkout pr-$PR_NUMBER

# Get file diff
git diff $EPIC_BRANCH...HEAD --stat
```

### 2. Read Changed Files

For each changed file:

1. Read the file content
2. Compare with project patterns
3. Check for learning application
4. Identify issues or suggestions

### 3. Generate Review Report

## Output Format

Post review as PR comment:

```markdown
## 🔍 Custom Reviewer Report

**PR**: #123
**Story**: STORY-001-1
**Verdict**: ✅ APPROVED / ⚠️ SUGGESTIONS / ❌ CHANGES_REQUIRED

---

### Architectural Fit

| Check                    | Status | Notes                          |
| ------------------------ | ------ | ------------------------------ |
| Follows project patterns | ✅     | Consistent with existing hooks |
| Correct file locations   | ✅     | All files in app/src/          |
| No hidden dependencies   | ✅     |                                |

### Learning Validation

**Applied Learnings:**

- ✅ L-ts001: Correctly imported vitest functions
- ✅ L-te003: Proper null checks added

**New Patterns Discovered:**

- [success] Audio context cleanup pattern for WebAudio API
- [optimization] Debounce voice input to reduce API calls

### Business Logic Review

| Criterion          | Status | Notes                               |
| ------------------ | ------ | ----------------------------------- |
| AC1: Voice capture | ✅     | Implemented with error handling     |
| AC2: Streaming     | ⚠️     | Edge case: slow network not handled |

### Performance

- ✅ No unnecessary re-renders detected
- ✅ Proper cleanup in useEffect

### Security

- ✅ No hardcoded values
- ✅ Input sanitization present

---

### Issues Found

1. **[SUGGESTION]** Consider adding network timeout handling
   - File: `app/src/hooks/useVoiceInput.ts:45`
   - Suggestion: Add timeout parameter to fetch call

2. **[CRITICAL]** Missing error boundary for audio failures
   - File: `app/src/components/VoiceInput.tsx`
   - Required: Wrap audio operations in try-catch

---

### Recommendation

**APPROVED** - Minor suggestions can be addressed in follow-up PR

OR

**CHANGES_REQUIRED** - Critical issue #2 must be fixed before merge
→ Spawn Fixer agent with: "Add error boundary for audio failures"
```

## Decision Matrix

| Findings               | Verdict          | Action                   |
| ---------------------- | ---------------- | ------------------------ |
| No issues              | APPROVED         | Proceed to Tester        |
| Minor suggestions only | APPROVED         | Note for future          |
| Non-critical issues    | SUGGESTIONS      | Proceed, track issues    |
| Critical issues        | CHANGES_REQUIRED | Spawn Fixer agent        |
| Architectural concerns | CHANGES_REQUIRED | Escalate to orchestrator |

## Model Selection

- **Model**: Haiku (read-only analysis)
- **Timeout**: 10 minutes max
- **Context budget**: ~50K tokens

## Integration Points

- **Orchestrator**: Receives review request, returns verdict
- **Fixer Agent**: If CHANGES_REQUIRED, orchestrator spawns Fixer
- **Tester Agent**: If APPROVED, orchestrator spawns Tester
- **Learning System**: Reports new patterns discovered
- **GitHub**: Posts review comment on PR
