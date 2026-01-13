# E2B Implementer Agent (DETERMINISTIC)

> Agent for implementing stories in E2B sandboxes with TDD workflow
> **CRITICAL**: Follow EXACT commands from E2B_EXECUTION_SPEC.md

## Overview

This agent runs in an E2B sandbox (not local) and implements a single story following TDD methodology. It has full access to the codebase via git clone and creates PRs when work is complete.

## Environment (VALIDATED - DO NOT CHANGE)

| Setting             | Value                        | Notes                        |
| ------------------- | ---------------------------- | ---------------------------- |
| **Sandbox**         | `anthropic-claude-code`      | Pre-built template           |
| **Working Dir**     | `/home/user/repo`            | NOT `/workspace`             |
| **App Dir**         | `/home/user/repo/app`        | Monorepo structure           |
| **Package Manager** | `npx pnpm`                   | NOT `pnpm` directly          |
| **PR Creation**     | GitHub REST API              | NOT `gh` CLI (unavailable)   |
| **Timeout**         | 10 minutes                   | Configurable in orchestrator |
| **Auth**            | Token via `GITHUB_TOKEN` env | Passed by orchestrator       |

## Inputs

The agent receives a **Task Brief** from the orchestrator with:

```json
{
  "storyId": "STORY-001-1",
  "title": "Voice Input Implementation",
  "scope": "voice",
  "acceptanceCriteria": ["AC1...", "AC2..."],
  "filesInScope": ["app/src/hooks/useVoiceInput.ts", "..."],
  "epicBranch": "epic/001-voice-input",
  "taskBranch": "task/001/T1-voice-input",
  "learnings": [{ "id": "L-ts001", "type": "failure", "learning": "..." }]
}
```

## Workflow (EXACT COMMANDS)

### 1. Setup (MANDATORY - EXACT COMMANDS)

```bash
# Step 1: Configure git (REQUIRED)
git config --global user.email "agent@e2b.dev"
git config --global user.name "E2B Agent"

# Step 2: Clone repository (TOKEN AUTH)
# Note: Repo is already cloned by sandbox setup
# If not, use: git clone --depth 1 --branch ${EPIC_BRANCH} https://${GITHUB_TOKEN}@github.com/${OWNER}/${REPO}.git /home/user/repo

# Step 3: Checkout task branch
cd /home/user/repo
git fetch --unshallow  # Get full history for branching
git checkout -b ${TASK_BRANCH}

# Step 4: Install dependencies (USE NPX PNPM - MANDATORY)
cd /home/user/repo/app
npx pnpm install --frozen-lockfile
```

### 2. TDD Cycle (MANDATORY)

**🔴 RED Phase (30% of time)**

1. Read acceptance criteria from task brief
2. Write failing tests for each criterion
3. Place tests in appropriate locations:
   - Unit tests: `app/src/**/*.test.ts`
   - Component tests: `app/src/components/**/__tests__/*.test.tsx`
4. Run tests - verify they FAIL:
   ```bash
   cd /home/user/repo/app
   npx pnpm test  # MUST show failures
   ```
5. Mark phase: `echo "🔴 RED complete" >> /home/user/repo/.ai/tdd-status.txt`

**🟢 GREEN Phase (50% of time)**

1. Implement minimum code to pass tests
2. Run tests frequently during implementation:
   ```bash
   cd /home/user/repo/app
   npx pnpm test
   ```
3. Fix failures immediately - don't accumulate
4. Verify ALL tests pass before proceeding
5. Mark phase: `echo "🟢 GREEN complete" >> /home/user/repo/.ai/tdd-status.txt`

**🔵 REFACTOR Phase (20% of time)**

1. Remove duplication
2. Improve naming and code structure
3. Extract reusable utilities if needed
4. Run tests - ensure still passing
5. Mark phase: `echo "🔵 REFACTOR complete" >> /home/user/repo/.ai/tdd-status.txt`

### 3. Quality Gates (ALL MUST PASS)

Run all gates in this order:

```bash
cd /home/user/repo/app

# Gate 1: TypeScript - MUST be 0 errors
npx pnpm typecheck
# IF exit code != 0 → STOP and fix

# Gate 2: Lint - MUST pass
npx pnpm lint
# IF exit code != 0 → STOP and fix

# Gate 3: Tests - ALL must pass
npx pnpm test
# IF exit code != 0 → STOP and fix
```

### 4. Self-Fix Protocol

If quality gates fail (max 3 attempts):

1. Parse error output
2. Apply fix based on learnings injected
3. Re-run quality gates
4. If still failing after 3 attempts, report as `BLOCKED`

### 5. Commit and Push (EXACT COMMANDS)

Only after ALL gates pass:

```bash
cd /home/user/repo

# Stage all changes
git add -A

# Commit with standard format
git commit -m "feat(${SCOPE}): ${STORY_TITLE}

Story: ${STORY_ID}
🔴🟢🔵 TDD workflow complete
Tests: X/X passing

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Push to origin
git push -u origin ${TASK_BRANCH}
```

### 6. Create PR (GitHub API - NOT gh CLI)

**CRITICAL**: The `gh` CLI is NOT available in E2B sandboxes. Use GitHub REST API.

Use the validated `github-api.js` utility:

```javascript
// At /home/user/repo/app/scripts/github-api.js
const { createPR, addLabels } = require("./scripts/github-api.js");

// Create PR
const pr = await createPR({
  owner: "${OWNER}",
  repo: "${REPO}",
  head: "${TASK_BRANCH}",
  base: "${EPIC_BRANCH}",
  title: "feat(${SCOPE}): ${STORY_TITLE}",
  body: prBody, // Generated from template below
  draft: false,
});

// Add required label
await addLabels({
  owner: "${OWNER}",
  repo: "${REPO}",
  prNumber: pr.number,
  labels: ["agent-generated"],
});
```

### 7. PR Body Template

Generate PR body with this format:

```markdown
## Summary

Implementation of ${STORY_ID}: ${STORY_TITLE}

## Acceptance Criteria

- [x] AC1...
- [x] AC2...

## Quality Gates

| Gate      | Command              | Result         |
| --------- | -------------------- | -------------- |
| TypeCheck | `npx pnpm typecheck` | ✅ 0 errors    |
| Lint      | `npx pnpm lint`      | ✅ 0 errors    |
| Tests     | `npx pnpm test`      | ✅ X/X passing |

## TDD Evidence

- 🔴 RED: Tests written first, verified failing
- 🟢 GREEN: Minimal implementation to pass
- 🔵 REFACTOR: Code cleaned, tests still green

## Learnings Applied

- ${LEARNING_1}
- ${LEARNING_2}

## New Patterns Discovered

- [success/failure/optimization]: [pattern description]

---

🤖 Generated with [Claude Code](https://claude.com/claude-code) via E2B Sandbox
```

## Output (EXACT JSON FORMAT)

Return this exact JSON structure to orchestrator:

```json
{
  "success": true|false,
  "storyId": "${STORY_ID}",
  "prNumber": <number>,
  "prUrl": "<url>",
  "branch": "${TASK_BRANCH}",
  "testsAdded": <count>,
  "testsPassing": <count>,
  "filesModified": ["<file1>", "<file2>"],
  "qualityGates": {
    "typecheck": "pass|fail",
    "lint": "pass|fail",
    "test": "pass|fail"
  },
  "durationMin": <minutes>,
  "newLearnings": [{ "type": "success|failure", "domain": "<domain>", "pattern": "<description>" }],
  "error": "<error message if success=false>"
}
```

## Model Selection

| Story Size | Model  |
| ---------- | ------ |
| XS (< 2hr) | Haiku  |
| S (2-4hr)  | Haiku  |
| M (4-8hr)  | Sonnet |
| L (1-2d)   | Sonnet |

## Context Management

- Read files JIT (Just-In-Time) - only when modifying
- Don't load entire codebase upfront
- Compact if context > 60%
- Keep focus on files in scope

## Failure Modes (DETERMINISTIC RESPONSES)

| Failure               | Response                            | Retry? |
| --------------------- | ----------------------------------- | ------ |
| TypeScript errors     | Apply learnings, fix, rerun gates   | Yes    |
| Lint errors           | Run `npx pnpm lint:fix`, verify     | Yes    |
| Test failures         | Debug and fix, max 3 attempts       | Yes    |
| Git push rejected     | Check auth, fetch and rebase, retry | Yes 1x |
| GitHub API rate limit | Wait for reset, retry               | Yes 2x |
| PR creation fails     | Return error with details           | No     |
| Max fix attempts (3)  | Report as `BLOCKED`                 | No     |
| Sandbox timeout       | Save progress, report incomplete    | No     |

## Reference

Full specification: `.claude/E2B_EXECUTION_SPEC.md`
