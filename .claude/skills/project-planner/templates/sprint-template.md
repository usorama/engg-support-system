# Sprint [NUMBER] Planning

## Sprint Metadata

| Field | Value |
|-------|-------|
| Sprint Number | [N] |
| Start Date | YYYY-MM-DD |
| End Date | YYYY-MM-DD |
| Duration | 2 weeks |
| Team Capacity | [X] story points |
| Sprint Goal | [One sentence describing the sprint objective] |

---

## Sprint Goals

### Primary Goal
> [What must be achieved for this sprint to be considered successful]

### Secondary Goals
- [ ] [Additional goal 1]
- [ ] [Additional goal 2]

### Success Criteria
1. [ ] All P0 tasks completed and verified
2. [ ] All tests passing with 80%+ coverage
3. [ ] No critical bugs in staging
4. [ ] Demo-ready for stakeholders

---

## Committed Stories

| ID | Title | Points | Priority | Status | Assignee |
|----|-------|--------|----------|--------|----------|
| TASK-001 | [Story title] | 3 | P0 | Pending | @dev1 |
| TASK-002 | [Story title] | 5 | P0 | Pending | @dev2 |
| TASK-003 | [Story title] | 2 | P1 | Pending | @dev1 |
| TASK-004 | [Story title] | 3 | P1 | Pending | @dev2 |
| TASK-005 | [Story title] | 1 | P2 | Pending | @dev1 |
| | **Total** | **14** | | | |

### Story Point Legend
| Points | Complexity | Time Estimate |
|--------|------------|---------------|
| 1 | Trivial | < 2 hours |
| 2 | Simple | 2-4 hours |
| 3 | Medium | 4-8 hours |
| 5 | Complex | 1-2 days |
| 8 | Very Complex | 2-3 days |
| 13 | Epic-sized | 3-5 days (consider splitting) |

---

## Sprint Backlog

### Day 1-2: Foundation
- [ ] TASK-001: [Description]
- [ ] TASK-002: [Description]

### Day 3-5: Core Implementation
- [ ] TASK-003: [Description]
- [ ] TASK-004: [Description]

### Day 6-8: Integration & Testing
- [ ] TASK-005: [Description]
- [ ] Code review and fixes

### Day 9-10: Polish & Release
- [ ] Bug fixes
- [ ] Documentation updates
- [ ] Staging deployment
- [ ] Demo preparation

---

## Dependencies & Blockers

### External Dependencies
| Dependency | Owner | Status | ETA | Impact |
|------------|-------|--------|-----|--------|
| [External API access] | [Team/Person] | Pending | [Date] | Blocks TASK-003 |
| [Design assets] | [Designer] | In Progress | [Date] | Blocks TASK-004 |

### Internal Dependencies
```
TASK-001 ──► TASK-003 ──► TASK-005
                │
TASK-002 ──────┘
```

### Current Blockers
| Blocker | Affected Tasks | Owner | Resolution Plan | ETA |
|---------|----------------|-------|-----------------|-----|
| [None] | - | - | - | - |

---

## Daily Capacity

| Day | Date | Available | Planned | Notes |
|-----|------|-----------|---------|-------|
| 1 | Mon | 16h | 14h | Sprint planning |
| 2 | Tue | 16h | 16h | |
| 3 | Wed | 16h | 16h | |
| 4 | Thu | 16h | 16h | |
| 5 | Fri | 16h | 14h | Code review focus |
| 6 | Mon | 16h | 16h | |
| 7 | Tue | 16h | 16h | |
| 8 | Wed | 16h | 16h | |
| 9 | Thu | 16h | 12h | Testing focus |
| 10 | Fri | 16h | 10h | Demo & retro |
| **Total** | | **160h** | **146h** | Buffer: 14h |

---

## Definition of Done Checklist

### Code Quality
- [ ] Code compiles without errors (`pnpm run typecheck`)
- [ ] Linting passes (`pnpm run lint`)
- [ ] No new TypeScript errors or warnings
- [ ] No `any` types introduced
- [ ] Code follows project conventions

### Testing
- [ ] Unit tests written and passing
- [ ] Test coverage >= 80%
- [ ] Integration tests passing (if applicable)
- [ ] Manual testing completed

### Review
- [ ] Code reviewed by at least 1 team member
- [ ] All review comments addressed
- [ ] PR approved

### Documentation
- [ ] Code comments added where needed
- [ ] README updated if public API changed
- [ ] CHANGELOG updated

### Deployment
- [ ] Deployed to staging environment
- [ ] Smoke tests pass on staging
- [ ] No console errors in production mode
- [ ] Performance metrics acceptable

---

## Burndown Tracking

### Daily Progress

| Day | Date | Planned Points | Completed Points | Remaining | Burndown |
|-----|------|----------------|------------------|-----------|----------|
| 0 | [Start] | 0 | 0 | 14 | ████████████████ |
| 1 | | 1 | | | |
| 2 | | 3 | | | |
| 3 | | 4 | | | |
| 4 | | 6 | | | |
| 5 | | 8 | | | |
| 6 | | 9 | | | |
| 7 | | 11 | | | |
| 8 | | 12 | | | |
| 9 | | 13 | | | |
| 10 | | 14 | | 0 | |

### Velocity
- Previous Sprint Velocity: [X] points
- Current Sprint Commitment: [Y] points
- Running Average: [Z] points

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [External API delays] | Medium | High | Have mock fallback ready |
| [Scope creep] | Low | Medium | Strict PR review process |
| [Technical debt] | Medium | Low | Allocate 20% time for cleanup |

---

## Sprint Retrospective

### What Went Well
1.
2.
3.

### What Could Be Improved
1.
2.
3.

### Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [@person] | [Date] | Pending |
| [Action 2] | [@person] | [Date] | Pending |

### Team Morale (1-5)
| Metric | Score | Notes |
|--------|-------|-------|
| Happiness | /5 | |
| Confidence | /5 | |
| Energy | /5 | |

---

## Notes

### Key Decisions Made
-

### Technical Debt Introduced
-

### Technical Debt Paid Off
-

---

*Last Updated: YYYY-MM-DD*
*Sprint Status: [Planning | In Progress | Complete]*
