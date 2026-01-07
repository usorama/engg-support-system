# Implementation Workflow (TDD: Specify → Test → Implement → Verify)

## Purpose
Define a deterministic, evidence-only, Test-Driven Development workflow that ensures specifications are written before implementation, tests are developed against those specs, and code is validated both pre and post implementation.

## TDD Pivots (2025-12-30)

### Key Changes from Previous Workflow
1. **New Step 0: Specification** - TDD specifications are written BEFORE any implementation
2. **New Step 1: Test Development** - Tests are defined BEFORE implementation
3. **Mandatory Pre-Implementation Test Run** - Establish baseline
4. **Test-Driven Implementation** - Code is written to make tests pass
5. **Post-Implementation Verification** - All tests must pass to proceed

## Global Rules
- **Evidence only**: If a required fact is not verified in the repo or logs, stop and request clarification.
- **TDD First**: Specifications are written before ANY implementation code.
- **Test-Driven**: Tests are written/defined BEFORE implementing features.
- **Use the story file as the single source of truth** for scope, steps, tests, and specifications.
- **Keep context minimal and scoped to the current step**.
- **Update progress after each step; never batch-complete items**.

## Workflow Stages

### 0) Specification (NEW - TDD Addition)
- Read the story requirements and business/technical constraints.
- Write TDD specifications in the story file's "TDD Specification" section.
- Specifications MUST be:
  - Observable (can be tested)
  - Measurable (has pass/fail criteria)
  - Unambiguous (no interpretation needed)
  - Independent (specs don't depend on implementation details)
- Specification format: **Given-When-Then** pattern

### 1) Test Development (NEW - TDD Addition)
- For each TDD specification, write/implement corresponding tests:
  - **Unit tests**: Test isolated components/behavior
  - **Integration tests**: Test component interactions
  - **Regression tests**: Verify no existing functionality breaks
- Tests MUST:
  - Be executable and passing (can start with failing tests)
  - Have clear assertions based on specification
  - Be deterministic (same inputs → same outputs)
- Run tests: **Pre-implementation baseline run** (should fail if implementation doesn't exist)

### 2) Research
- Read the story file and its linked references.
- Inspect only the files specified in the story.
- Produce a short research summary inside the story file.
- If gaps remain, add explicit questions under "Blocked / Needs Clarification" and stop.

### 3) Understand
- Restate the problem and current-state facts with file-path evidence.
- Validate assumptions; any unverified assumption must be converted into a question.

### 4) Decide (Plan Refinement)
- Confirm step order, inputs, outputs, and test coverage.
- If the plan needs refinement, update the story checklist and DoD before implementation.
- Do not implement anything until:
  - TDD specifications are written
  - Tests are defined
  - DoR is satisfied

### 5) Implement
- Execute steps one at a time in the order listed.
- Make minimal changes tied to the step.
- Run tests **after each implementation step**:
  - Tests should start passing as implementation progresses
  - If tests fail unexpectedly, stop and debug
  - Never proceed with failing tests
- Record each completed step with a timestamp in the story file.

### 6) Test (Post-Implementation)
- Run all unit, integration, and regression checks listed in the story.
- Capture test commands and outcomes in the story file.
- **ALL tests MUST pass** to proceed
- If tests fail:
  - Stop and document failures
  - Fix implementation to satisfy tests
  - Re-run until all pass
  - Do NOT proceed until all tests pass

### 7) Refine
- Fix only what is required by failed tests or unmet DoD.
- Re-run impacted tests and update the story file.

### 8) Verify
- Verify outputs against success criteria.
- Re-check determinism requirements (repeatable outputs, pinned versions).
- **Final test run**: Full test suite must pass

### 9) Update Progress
- Update `docs/plans/MASTER_TASKS.md` for the story status.
- Update story checklists and notes.

## TDD Specification Guidelines

### Given-When-Then Pattern

```
Specification #N: [Short Name]

Given [preconditions and context]
When [action or event occurs]
Then [expected outcomes are observable]

Acceptance Criteria:
- [Specific, measurable condition 1]
- [Specific, measurable condition 2]
```

### Example
```
Specification 1: Configuration Hierarchy

Given multiple configuration sources exist
When configuration is loaded
Then final configuration should be:
1. Start with defaults
2. Override with config file if present
3. Override with environment variables if present
4. Override with CLI arguments if present
In that specific order

Acceptance Criteria:
- Default config loads when no other sources present
- Config file overrides defaults
- Env vars override config file
- CLI args override env vars
```

## Quality Gates

### Cannot Proceed Unless:
- [x] All TDD specifications written
- [x] Tests defined for each specification
- [x] Pre-implementation baseline recorded
- [x] All tests pass post-implementation
- [x] All acceptance criteria met

## Commit and Rollback

### Commit Criteria
- All specifications written
- ALL tests pass
- DoD satisfied

### Commit Message
```
story-XYZ: summary
Specs: N written
Tests: M/M passing (100%)
DoD: Satisfied
```

### Rollback
If failing and unfixable in scope:
1. Revert changes
2. Document blocker in story file
3. Update MASTER_TASKS.md status to "BLOCKED"

## Per-Story Artifacts
1. TDD Specifications (story file)
2. Test definitions/implementations (test files)
3. Test results (pre + post implementation)
4. Research summary (story file)
5. DoD checklist (story file)
