# Implementation Orchestration Plan

> How stories become working software through coordinated agent execution

---

## Document Context

| Field                | Value                     |
| -------------------- | ------------------------- |
| **Project**          | [Project Name]            |
| **Sprint**           | [Sprint Number/Name]      |
| **Created**          | [Date]                    |
| **Stories in Scope** | [Count] from `tasks.json` |

**References**:

- Sprint Plan: `docs/sprints/sprint-XXX.md`
- Stories: `docs/tasks/kanban_board.md`
- Tasks: `docs/tasks/tasks.json`
- Architecture: `docs/planning/ARCHITECTURE.md`

---

## 1. Agent Team

### Orchestrator

| Attribute   | Value                                              |
| ----------- | -------------------------------------------------- |
| **Model**   | [Opus 4.5 / Sonnet 4]                              |
| **Role**    | Coordinate execution, verify outputs, manage state |
| **Context** | Stakeholder profile, this plan, PROGRESS.md        |

### Execution Agents

| Agent     | Model                | Specialization         | Tools                   |
| --------- | -------------------- | ---------------------- | ----------------------- |
| Builder   | Haiku 4.5 / Sonnet 4 | Code implementation    | Read, Write, Edit, Bash |
| Validator | Haiku 4.5            | Tests, lint, typecheck | Bash, Read, Grep        |
| Reviewer  | Sonnet 4             | Code review, security  | Read, Grep, Glob        |

**Model Selection Rationale**:

- Haiku for repetitive/simple tasks (90% capability, 3x cheaper)
- Sonnet for code generation and review
- Opus only for orchestration and critical decisions

---

## 2. Story Execution Map

### Dependency Graph

```
[US-001] ─────┐
              ├──→ [US-004] ──→ [US-006]
[US-002] ─────┘

[US-003] ──────────→ [US-005]
```

### Execution Waves

Stories grouped by dependencies. Each wave can run in parallel.

#### Wave 1: Foundation (Sequential within, blocks Wave 2)

| Story  | Title   | Agent   | Model  | Est.    | Dependencies |
| ------ | ------- | ------- | ------ | ------- | ------------ |
| US-001 | [Title] | Builder | Sonnet | [S/M/L] | None         |
| US-002 | [Title] | Builder | Sonnet | [S/M/L] | None         |
| US-003 | [Title] | Builder | Sonnet | [S/M/L] | None         |

**Wave 1 Quality Gate**: All stories pass typecheck, lint, tests before Wave 2.

#### Wave 2: Core Features (Parallel)

| Story  | Title   | Agent   | Model | Est.    | Dependencies   |
| ------ | ------- | ------- | ----- | ------- | -------------- |
| US-004 | [Title] | Builder | Haiku | [S/M/L] | US-001, US-002 |
| US-005 | [Title] | Builder | Haiku | [S/M/L] | US-003         |

**Parallel Strategy**: Spawn agents A, B simultaneously. No shared file conflicts.

#### Wave 3: Integration (Sequential)

| Story  | Title   | Agent   | Model  | Est.    | Dependencies |
| ------ | ------- | ------- | ------ | ------- | ------------ |
| US-006 | [Title] | Builder | Sonnet | [S/M/L] | US-004       |

---

## 3. Velocity vs Quality Balance

### Quality Gates (Non-Negotiable)

Every story completion requires:

```
□ pnpm typecheck → 0 errors
□ pnpm lint → 0 errors
□ pnpm test → all pass
□ No hardcoded values
□ Reviewer agent approval (for M/L stories)
```

### Velocity Optimizations

| Strategy                   | When to Apply                            |
| -------------------------- | ---------------------------------------- |
| **Parallel waves**         | Stories with no shared dependencies      |
| **Haiku for simple tasks** | S-sized stories, validation, formatting  |
| **Skip reviewer**          | XS/S stories with high test coverage     |
| **Batch similar work**     | Multiple stories touching same component |

### Quality vs Speed Decision Matrix

| Story Size | Reviewer?      | Full Test Suite?   | Model  |
| ---------- | -------------- | ------------------ | ------ |
| XS (< 2hr) | No             | Unit only          | Haiku  |
| S (2-4hr)  | Optional       | Unit only          | Haiku  |
| M (4-8hr)  | Yes            | Unit + Integration | Sonnet |
| L (1-2d)   | Yes            | Full suite         | Sonnet |
| XL (2-3d)  | Yes + 2nd pass | Full + E2E         | Sonnet |

---

## 4. Integration Points

### How Stories Connect

| Integration Point | Stories Involved | Verification     |
| ----------------- | ---------------- | ---------------- |
| [Auth → API]      | US-001 → US-004  | Integration test |
| [API → UI]        | US-004 → US-006  | E2E test         |
| [DB → Service]    | US-002 → US-005  | Integration test |

### Integration Testing Strategy

```
Wave 1 complete → Run integration tests for foundation
Wave 2 complete → Run integration tests for features
Wave 3 complete → Run full E2E suite
```

---

## 5. Agent Prompt Templates

### Builder Agent Prompt

```
## Context
- Story: [US-XXX] [Title]
- From: docs/tasks/kanban_board.md
- Files in scope: [list files]

## Objective
Implement [specific outcome] that:
- Achieves: [business outcome]
- Provides: [user experience]
- Meets: [technical standard]

## Constraints
- No hardcoded values (use env/config)
- Match existing code patterns in [reference file]
- Quality gates must pass

## Verification (before reporting complete)
- [ ] Code compiles (0 errors)
- [ ] Tests written and passing
- [ ] No hardcoded secrets/URLs
- [ ] Lint passes
```

### Validator Agent Prompt

```
## Context
- Validating: [US-XXX] implementation
- Files changed: [list]

## Checks Required
1. pnpm typecheck
2. pnpm lint
3. pnpm test --coverage
4. grep for hardcoded values

## Report Format
✓ Check passed / ✗ Check failed: [specific error]
```

---

## 6. Error Recovery

### If Story Implementation Fails

```
Attempt 1: Builder tries alternate approach
Attempt 2: Escalate to Sonnet model
Attempt 3: Flag for human review
```

### If Quality Gate Fails

```
1. Validator identifies specific failure
2. Spawn fix agent with narrow scope
3. Re-run quality gate
4. Max 3 attempts → human escalation
```

### If Integration Fails

```
1. Identify which story broke integration
2. Rollback that story's changes
3. Fix in isolation
4. Re-integrate
```

---

## 7. Progress Checkpoints

| Checkpoint        | Trigger                  | Save To           |
| ----------------- | ------------------------ | ----------------- |
| Wave complete     | All stories in wave done | .ai/PROGRESS.md   |
| Quality gate pass | After each story         | tasks.json status |
| Integration pass  | After wave integration   | .ai/PROGRESS.md   |
| Session end       | Before stopping          | .ai/PROGRESS.md   |

---

## 8. Current Execution Status

### Wave Progress

| Wave | Stories | Complete | In Progress | Blocked |
| ---- | ------- | -------- | ----------- | ------- |
| 1    | 3       | 0        | 0           | 0       |
| 2    | 2       | 0        | 0           | 0       |
| 3    | 1       | 0        | 0           | 0       |

### Active Agents

| Agent | Working On | Status | Started |
| ----- | ---------- | ------ | ------- |
| -     | -          | Idle   | -       |

---

## Quick Reference

```
Execution Command:
"Execute Wave [N] of the implementation plan.
 Spawn parallel agents for independent stories.
 Verify quality gates before marking complete.
 Update PROGRESS.md after each story."
```

---

_This plan is generated from sprint/epic/story data and updated during execution._
