---
name: execute
description: Deterministic plan execution with mathematical certainty. Use for implementing IMPLEMENTATION-PLAN.md files with triple verification, git workflow, and cross-session context sharing. Works identically for rad-engineer-v2 and engg-support-system.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, TodoWrite, mcp__memory-keeper__context_save, mcp__memory-keeper__context_get, mcp__memory-keeper__context_checkpoint
model: claude-sonnet-4-20250514
---

# Deterministic Plan Execution Skill

## Purpose

Execute implementation plans with **mathematical certainty**:
- Triple verification on every task
- Same inputs → Same outputs (drift rate 0%)
- Evidence-based completion proofs
- Cross-session context sharing via files + memory-keeper

**Works identically for**: rad-engineer-v2, engg-support-system, any future project

---

## Core Protocol: Validate-Execute-Verify Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                 DETERMINISTIC EXECUTION LOOP                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   START                                                         │
│     │                                                           │
│     ▼                                                           │
│   ┌─────────────────┐                                          │
│   │ 1. VALIDATE     │ ◄── Check preconditions                  │
│   │    Preconditions│     Files exist? Deps met? Env ready?    │
│   └────────┬────────┘                                          │
│            │ PASS                                               │
│            ▼                                                    │
│   ┌─────────────────┐                                          │
│   │ 2. CREATE TEST  │ ◄── TDD: Write failing test first        │
│   │    (TDD Red)    │                                          │
│   └────────┬────────┘                                          │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐                                          │
│   │ 3. EXECUTE      │ ◄── Implement to pass test               │
│   │    Implementation│     Capture all outputs                  │
│   └────────┬────────┘                                          │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐     ┌─────────────────┐                  │
│   │ 4. VERIFY       │ NO  │ 5. FIX & RETRY  │                  │
│   │    Postconditions├───►│    (max 3)      │                  │
│   └────────┬────────┘     └────────┬────────┘                  │
│            │ PASS                  │                            │
│            │◄──────────────────────┘                            │
│            ▼                                                    │
│   ┌─────────────────┐                                          │
│   │ 6. CAPTURE      │ ◄── Evidence + Git commit                │
│   │    Evidence     │                                          │
│   └────────┬────────┘                                          │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐                                          │
│   │ 7. UPDATE       │ ◄── Progress file + memory-keeper        │
│   │    Progress     │                                          │
│   └────────┬────────┘                                          │
│            │                                                    │
│            ▼                                                    │
│        NEXT TASK                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Startup Protocol

### Step 1: Identify Project Context

```bash
# Determine which project we're executing for
if [[ -f "docs/platform-foundation/RAD-ENGINEER-IMPLEMENTATION-PLAN.md" ]]; then
  PROJECT="rad-engineer-v2"
  PLAN_FILE="docs/platform-foundation/RAD-ENGINEER-IMPLEMENTATION-PLAN.md"
  TEST_CMD="bun test"
  TYPECHECK_CMD="bun run typecheck"
  WORKING_DIR="rad-engineer"
elif [[ -f "docs/platform-foundation/engg-support-system/IMPLEMENTATION-PLAN.md" ]]; then
  PROJECT="engg-support-system"
  PLAN_FILE="docs/platform-foundation/engg-support-system/IMPLEMENTATION-PLAN.md"
  TEST_CMD="bun test && pytest"  # Both TS and Python
  TYPECHECK_CMD="bun run typecheck"
  WORKING_DIR="."
fi
```

### Step 2: Load Required Context

```markdown
Required reads (in order):
1. ${PLAN_FILE} → Implementation plan with tasks
2. docs/platform-foundation/PLAN-EXECUTION-DETERMINISM.md → Verification protocol
3. docs/platform-foundation/INTEGRATION-DEPENDENCIES.md → Cross-system deps
4. docs/platform-foundation/ANALYSIS-MEMORY.yaml → Current progress
5. mcp_context_get(category: "progress") → Memory-keeper state
```

### Step 3: Determine Current State

```markdown
Parse from ANALYSIS-MEMORY.yaml and memory-keeper:
- Current phase number
- Last completed task
- Any blocked tasks
- Next task to execute
```

### Step 4: Check Integration Dependencies (if applicable)

```markdown
If task has ESS dependency:
1. Read docs/platform-foundation/engg-support-system/INTEGRATION-STATUS.md
2. Check if required checkpoint is COMPLETE
3. If not complete: Skip to independent task OR wait

If executing ESS:
1. After phase completion, update INTEGRATION-STATUS.md
2. Signal rad-engineer-v2 session via file update
```

### Step 5: Report Status Before Execution

```markdown
## Execution Status

**Project**: ${PROJECT}
**Current Phase**: [N] - [Name]
**Tasks**: [Complete]/[Total] in this phase

### Ready to Execute
| Task | Description | Preconditions | Estimated |
|------|-------------|---------------|-----------|
| X.Y.Z | [Description] | [Status] | [Time] |

### Dependencies
| Task | Depends On | Status |
|------|------------|--------|
| [task] | [dependency] | [ready/blocked] |

Proceeding with execution...
```

---

## Task Execution Protocol

### For Each Task

#### 1. VALIDATE Preconditions

```bash
# Check file existence
for file in ${REQUIRED_FILES}; do
  if [[ ! -f "$file" ]]; then
    echo "PRECONDITION FAILED: $file does not exist"
    exit 1
  fi
done

# Check environment
if [[ -z "${REQUIRED_ENV_VAR}" ]]; then
  echo "PRECONDITION FAILED: $REQUIRED_ENV_VAR not set"
  exit 1
fi

# Check dependencies (from INTEGRATION-DEPENDENCIES.md)
if [[ "$DEPENDS_ON_ESS" == "true" ]]; then
  grep -q "Phase ${REQUIRED_PHASE}.*COMPLETE" docs/platform-foundation/engg-support-system/INTEGRATION-STATUS.md
  if [[ $? -ne 0 ]]; then
    echo "PRECONDITION FAILED: ESS Phase ${REQUIRED_PHASE} not complete"
    echo "Skip to independent task or wait for ESS"
    exit 1
  fi
fi

echo "All preconditions PASSED"
```

#### 2. CREATE Test (TDD Red Phase)

```markdown
**MANDATORY**: Write failing test BEFORE implementation

1. Create test file if not exists
2. Write test cases for:
   - Each acceptance criterion
   - Edge cases
   - Error conditions
3. Run tests - MUST FAIL
4. Log test output as evidence
```

#### 3. EXECUTE Implementation

```markdown
**Agent spawning for implementation**:

Task(
  subagent_type="developer",
  description="Implement task ${TASK_ID}",
  prompt="""
Task: ${TASK_DESCRIPTION}
Files: ${FILES_TO_CREATE_OR_MODIFY}
Output: JSON {filesModified, summary, errors, testsPassing}

## Preconditions (Already Verified)
${PRECONDITION_EVIDENCE}

## Test File (Already Created - Make These Pass)
${TEST_FILE_PATH}

## TDD Workflow
1. Run tests - confirm they fail
2. Implement minimum code to pass
3. Refactor while keeping tests green

## Quality Gates (Before Completion)
${TEST_CMD}
${TYPECHECK_CMD}

## Evidence Required
Include in response:
- Command outputs for all quality gates
- Files created/modified with line counts
- Test results (passing/failing)
"""
)
```

#### 4. VERIFY Postconditions

```bash
# Run quality gates
cd ${WORKING_DIR}

echo "Running typecheck..."
${TYPECHECK_CMD}
TYPECHECK_RESULT=$?

echo "Running tests..."
${TEST_CMD}
TEST_RESULT=$?

# Check success criteria from plan
if [[ $TYPECHECK_RESULT -ne 0 ]]; then
  echo "POSTCONDITION FAILED: Typecheck errors"
  exit 1
fi

if [[ $TEST_RESULT -ne 0 ]]; then
  echo "POSTCONDITION FAILED: Tests failing"
  exit 1
fi

# Verify files exist (from task spec)
for file in ${EXPECTED_FILES}; do
  if [[ ! -f "$file" ]]; then
    echo "POSTCONDITION FAILED: Expected file $file not created"
    exit 1
  fi
done

echo "All postconditions PASSED"
```

#### 5. FIX & RETRY (if failed)

```markdown
Retry Protocol (max 3 attempts):

Attempt 1: Re-run with error context
  - Include previous error message
  - Same agent, same approach

Attempt 2: Alternative approach
  - Analyze failure pattern
  - Try different implementation strategy

Attempt 3: Escalate
  - Use higher-capability model
  - Or mark as BLOCKED with detailed reason

After 3 failures:
  - Mark task as BLOCKED in progress file
  - Continue with independent tasks
  - Alert user if on critical path
```

#### 6. CAPTURE Evidence

```markdown
## Task Completion Proof: ${TASK_ID}

### Preconditions Verified
- [x] File A exists: `ls -la path/to/file` ✓
- [x] Dependency B met: [evidence]

### Implementation Evidence
- Files created: [list with line counts]
- Test coverage: [percentage]
- Quality gates: all pass

### Postconditions Verified
```
$ ${TYPECHECK_CMD}
[actual output - 0 errors]

$ ${TEST_CMD}
[actual output - all pass]
```

### Git Commit
```
$ git add -A && git commit -m "${COMMIT_MSG}"
[commit hash]
```

### Timestamp
${ISO_TIMESTAMP}
```

#### 7. UPDATE Progress

```bash
# Update ANALYSIS-MEMORY.yaml
cat >> docs/platform-foundation/ANALYSIS-MEMORY.yaml << EOF
    - timestamp: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      task_id: "${TASK_ID}"
      action: "VERIFIED"
      summary: "${SUMMARY}"
      evidence:
        typecheck: "0 errors"
        tests: "${TESTS_PASSING} passed"
        files: ${FILES_LIST}
EOF

# Update memory-keeper
mcp_context_save(
  category: "progress",
  key: "task-${TASK_ID}-complete",
  value: "${COMPLETION_PROOF_JSON}",
  priority: "high"
)

# Git commit for progress
git add docs/platform-foundation/ANALYSIS-MEMORY.yaml
git commit -m "progress: Complete ${TASK_ID}"
```

---

## Git Workflow

### Commit Protocol

```markdown
Every task completion gets a git commit:

1. **Implementation commit**:
   git commit -m "feat(${COMPONENT}): ${TASK_DESCRIPTION}

   Task: ${TASK_ID}
   Phase: ${PHASE_NUMBER}

   - Files: ${FILES_LIST}
   - Tests: ${TEST_COUNT} passing
   - Coverage: ${COVERAGE}%

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

2. **Progress commit**:
   git commit -m "progress: Complete ${TASK_ID}

   Verification evidence captured.
   Next: ${NEXT_TASK_ID}"
```

### Checkpoint Protocol

```markdown
After each PHASE completion:

1. Create git tag:
   git tag -a "phase-${PHASE_NUMBER}-complete" -m "Phase ${PHASE_NUMBER} verified"

2. Create memory-keeper checkpoint:
   mcp_context_checkpoint(name: "phase-${PHASE_NUMBER}-complete")

3. Update integration status (if ESS):
   Edit docs/platform-foundation/engg-support-system/INTEGRATION-STATUS.md
   Mark phase as COMPLETE with timestamp
```

### Push Protocol

```markdown
Push to remote after:
- Each phase completion
- Before stopping work
- After any significant milestone

git push origin ${BRANCH}
git push --tags  # for checkpoints
```

---

## Cross-Session Context Sharing

### File-Based Sharing

```markdown
Both sessions share these files (via git):

1. INTEGRATION-DEPENDENCIES.md
   - What rad-engineer needs from ESS
   - Updated by orchestrator

2. engg-support-system/INTEGRATION-STATUS.md
   - Phase completion status
   - Updated by ESS session

3. ANALYSIS-MEMORY.yaml
   - Per-project progress
   - Updated by both sessions

Sync protocol:
- Before starting: git pull
- After phase: git push
- Check for updates: git fetch && git diff origin/main
```

### Memory-Keeper Sharing

```markdown
Use channels for cross-session context:

# ESS session saves:
mcp_context_save(
  category: "progress",
  channel: "ess-integration",
  key: "phase-2-http-gateway",
  value: "COMPLETE - endpoint /query working"
)

# rad-engineer session reads:
mcp_context_get(channel: "ess-integration")
```

---

## Metrics Collection

### Per-Task Metrics

```yaml
task_metrics:
  task_id: "1.1.1"
  start_time: "2026-01-13T10:00:00Z"
  end_time: "2026-01-13T10:45:00Z"
  duration_minutes: 45
  attempts: 1
  first_pass: true
  typecheck_errors: 0
  tests_passing: 12
  tests_total: 12
  files_created: 2
  files_modified: 0
  lines_added: 245
```

### Per-Phase Metrics

```yaml
phase_metrics:
  phase: 1
  name: "Hierarchical Memory"
  start_time: "2026-01-13T10:00:00Z"
  end_time: "2026-01-13T16:00:00Z"
  tasks_total: 12
  tasks_complete: 12
  tasks_blocked: 0
  first_pass_rate: 0.83
  total_attempts: 15
  test_coverage: 0.87
  verification_pass_rate: 1.0
```

### Drift Detection (Optional)

```markdown
After critical tasks, optionally run drift check:

1. Capture task input hash
2. Run task 3 times
3. Compare AST of outputs
4. Log variance

Target: 0% drift (identical outputs)
```

---

## Error Recovery

### Task Failure

```markdown
On postcondition failure:

1. Log error details
2. Increment attempt counter
3. If attempt < 3:
   - Analyze failure pattern
   - Adjust approach
   - Retry
4. If attempt >= 3:
   - Mark as BLOCKED
   - Document reason
   - Continue with independent tasks
```

### Integration Failure

```markdown
If ESS is unavailable when rad-engineer needs it:

1. Check INTEGRATION-STATUS.md
2. If ESS phase not complete:
   - Skip dependent tasks
   - Work on independent tasks
   - Save state for later
3. Document in progress file
```

### Session Interruption

```markdown
On session end (graceful or crash):

1. Save all state to memory-keeper
2. Update progress files
3. Commit to git

On session resume:
1. Read memory-keeper state
2. Read progress files
3. Identify last completed task
4. Resume from next task
```

---

## Usage Examples

### Execute Next Task

```
/execute
```
Automatically identifies next task and executes with full verification.

### Execute Specific Phase

```
/execute phase 2
```
Executes all tasks in Phase 2.

### Execute Specific Task

```
/execute task 1.1.3
```
Executes task 1.1.3 with full verification.

### Check Status Only

```
/execute status
```
Reports current progress without executing.

### Resume After Interruption

```
/execute resume
```
Recovers state and continues from last checkpoint.

---

## Quality Standards (Non-Negotiable)

These apply to ALL tasks in ALL projects:

- [ ] No `any` types in TypeScript
- [ ] All tests passing
- [ ] Typecheck clean (0 errors)
- [ ] Evidence captured for every task
- [ ] Git commit after every task
- [ ] Progress file updated after every task
- [ ] Memory-keeper checkpoint after every phase

---

## Integration with Other Skills

| Skill | When to Use |
|-------|-------------|
| `/verify-task` | Verify specific task completion |
| `/plan` | Generate execution plan before this skill |
| `/code-review` | After implementation, before commit |
| `/progress-tracker` | Quick status check |

---

## Mathematical Certainty Definition

A task is **mathematically complete** when:

```
COMPLETE(task) ⟺
  ∀ precondition ∈ task.preconditions: precondition = TRUE
  ∧ ∀ postcondition ∈ task.postconditions: postcondition = TRUE
  ∧ tests.all_pass = TRUE
  ∧ typecheck.errors = 0
  ∧ evidence.captured = TRUE
  ∧ git.committed = TRUE
  ∧ progress.updated = TRUE
```

This is verified by the skill for every task execution.

---

**Version**: 1.0.0
**Created**: 2026-01-13
**Works With**: rad-engineer-v2, engg-support-system, any IMPLEMENTATION-PLAN.md
