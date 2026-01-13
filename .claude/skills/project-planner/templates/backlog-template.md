# Product Backlog

## Backlog Overview

| Category | Count | Total Points |
|----------|-------|--------------|
| MVP (P0-P1) | 0 | 0 |
| Future (P2-P3) | 0 | 0 |
| Technical Debt | 0 | 0 |
| **Total** | **0** | **0** |

*Last Updated: YYYY-MM-DD*
*Backlog Health: [Healthy | Needs Grooming | Stale]*

---

## MVP Items (P0-P1)

### P0 - Critical / Must Have

> These items are required for launch. No MVP without them.

| ID | Title | Points | RICE Score | Dependencies | Sprint |
|----|-------|--------|------------|--------------|--------|
| TASK-001 | [Feature title] | 5 | 85 | - | 1 |
| TASK-002 | [Feature title] | 8 | 82 | TASK-001 | 1 |
| TASK-003 | [Feature title] | 3 | 78 | - | 2 |

#### P0 Details

<details>
<summary>TASK-001: [Feature Title]</summary>

**Description:**
[Detailed description of the feature]

**User Story:**
As a [user type], I want to [action] so that [benefit].

**Acceptance Criteria:**
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

**Technical Notes:**
- [Implementation consideration 1]
- [Implementation consideration 2]

**Effort Breakdown:**
| Component | Points |
|-----------|--------|
| Backend | 2 |
| Frontend | 2 |
| Testing | 1 |
| **Total** | **5** |

</details>

---

### P1 - High Priority / Should Have

> Important for MVP but could be descoped if needed.

| ID | Title | Points | RICE Score | Dependencies | Sprint |
|----|-------|--------|------------|--------------|--------|
| TASK-010 | [Feature title] | 5 | 65 | TASK-001 | 2 |
| TASK-011 | [Feature title] | 3 | 62 | - | 2 |
| TASK-012 | [Feature title] | 8 | 58 | TASK-002 | 3 |

---

## Future Items (P2-P3)

### P2 - Medium Priority / Nice to Have

> Enhance user experience but not critical for launch.

| ID | Title | Points | RICE Score | Dependencies | Target |
|----|-------|--------|------------|--------------|--------|
| TASK-020 | [Feature title] | 5 | 45 | - | Post-MVP |
| TASK-021 | [Feature title] | 8 | 42 | TASK-010 | Q2 |
| TASK-022 | [Feature title] | 3 | 38 | - | Q2 |

### P3 - Low Priority / Future Consideration

> Long-term improvements and wishlist items.

| ID | Title | Points | RICE Score | Dependencies | Target |
|----|-------|--------|------------|--------------|--------|
| TASK-030 | [Feature title] | 13 | 25 | - | Q3+ |
| TASK-031 | [Feature title] | 8 | 22 | - | Q3+ |
| TASK-032 | [Feature title] | 5 | 18 | TASK-030 | Q4 |

---

## Technical Debt

| ID | Title | Points | Impact | Urgency | Sprint |
|----|-------|--------|--------|---------|--------|
| DEBT-001 | [Debt item] | 3 | High | Medium | 2 |
| DEBT-002 | [Debt item] | 2 | Medium | Low | 3 |
| DEBT-003 | [Debt item] | 5 | High | High | 1 |

---

## Prioritization Framework: RICE

### RICE Score Calculation

```
RICE Score = (Reach × Impact × Confidence) / Effort
```

| Factor | Description | Scale |
|--------|-------------|-------|
| **Reach** | How many users will this impact per quarter? | Actual number (100, 1000, 10000) |
| **Impact** | How much will this impact each user? | 3=Massive, 2=High, 1=Medium, 0.5=Low, 0.25=Minimal |
| **Confidence** | How confident are we in our estimates? | 100%=High, 80%=Medium, 50%=Low |
| **Effort** | Person-months of work | 0.5, 1, 2, 3, 6, 12 |

### RICE Scoring Example

| Item | Reach | Impact | Confidence | Effort | Score |
|------|-------|--------|------------|--------|-------|
| Feature A | 5000 | 2 | 80% | 2 | (5000×2×0.8)/2 = **4000** |
| Feature B | 1000 | 3 | 100% | 3 | (1000×3×1.0)/3 = **1000** |
| Feature C | 10000 | 0.5 | 50% | 0.5 | (10000×0.5×0.5)/0.5 = **5000** |

### Alternative: MoSCoW Method

| Category | Description |
|----------|-------------|
| **Must have** | Critical for delivery, non-negotiable |
| **Should have** | Important but not vital, can be workaround |
| **Could have** | Desirable but not necessary, nice-to-have |
| **Won't have** | Not a priority this time, future consideration |

---

## Dependencies Map

### Visual Dependency Graph

```
Phase 0: Foundation
├── TASK-001 (Setup)
│   ├── TASK-002 (CI/CD)
│   └── TASK-003 (Config)
│
Phase 1: Core
├── TASK-010 (Core Feature A)
│   ├── TASK-011 (depends on 010)
│   └── TASK-012 (depends on 010)
├── TASK-013 (Core Feature B)
│   └── TASK-014 (depends on 013)
│
Phase 2: Enhancement
├── TASK-020 (depends on 011, 012)
└── TASK-021 (depends on 014)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|------------|--------|
| TASK-001 | - | TASK-002, TASK-003, TASK-010 |
| TASK-002 | TASK-001 | TASK-050 |
| TASK-010 | TASK-001 | TASK-011, TASK-012 |
| TASK-011 | TASK-010 | TASK-020 |

### Critical Path
```
TASK-001 → TASK-010 → TASK-011 → TASK-020 → TASK-030
```
*Estimated duration: 25 story points / ~3 sprints*

---

## Effort Estimates

### T-Shirt Sizing to Story Points

| Size | Story Points | Typical Duration | Examples |
|------|--------------|------------------|----------|
| XS | 1 | < 2 hours | Config change, typo fix |
| S | 2 | 2-4 hours | Simple component, bug fix |
| M | 3-5 | 4-16 hours | Feature slice, integration |
| L | 8 | 2-3 days | Complete feature, refactor |
| XL | 13 | 3-5 days | Epic, major system change |
| XXL | 21+ | 1+ week | **Split required** |

### Estimation Checklist

Before estimating, consider:
- [ ] Backend work required?
- [ ] Frontend work required?
- [ ] Database changes?
- [ ] Third-party integrations?
- [ ] Testing effort?
- [ ] Documentation needs?
- [ ] Code review time?
- [ ] Risk/uncertainty buffer?

---

## Backlog Grooming Checklist

### Weekly Grooming Session
- [ ] Review new items added to backlog
- [ ] Ensure all items have clear descriptions
- [ ] Verify acceptance criteria are defined
- [ ] Update RICE scores for changed context
- [ ] Remove stale/obsolete items
- [ ] Break down items that are too large (>13 points)
- [ ] Update dependencies
- [ ] Confirm estimates are still accurate
- [ ] Identify items ready for next sprint

### Healthy Backlog Criteria
- [ ] At least 2 sprints of ready items (P0-P1)
- [ ] All P0 items have acceptance criteria
- [ ] No items larger than 13 points
- [ ] Dependencies clearly mapped
- [ ] Items ordered by priority
- [ ] Recent (< 2 weeks) RICE scores

---

## Epics & Themes

### Epic: [Epic Name]

| Field | Value |
|-------|-------|
| Epic ID | EPIC-001 |
| Owner | @person |
| Target | Q1 2025 |
| Status | In Progress |

**Objective:** [What this epic achieves]

**Success Metrics:**
- Metric 1: [target]
- Metric 2: [target]

**Child Stories:**
- [ ] TASK-001 (5 pts) - Completed
- [ ] TASK-002 (8 pts) - In Progress
- [ ] TASK-003 (3 pts) - Pending

**Progress:** 5/16 points (31%)

---

## Parking Lot

> Ideas and suggestions that need more research before backlog inclusion.

| Idea | Source | Added | Notes |
|------|--------|-------|-------|
| [Idea 1] | User feedback | 2025-01-01 | Needs user research |
| [Idea 2] | Team suggestion | 2025-01-05 | Pending technical feasibility |
| [Idea 3] | Competitor analysis | 2025-01-10 | Low priority |

---

## Appendix

### Story Point Velocity History

| Sprint | Committed | Completed | Velocity |
|--------|-----------|-----------|----------|
| 1 | 15 | 12 | 12 |
| 2 | 14 | 14 | 14 |
| 3 | 16 | 15 | 15 |
| **Average** | | | **13.7** |

### Backlog Changelog

| Date | Change | By |
|------|--------|-----|
| 2025-01-01 | Initial backlog created | @pm |
| 2025-01-08 | Added P0 items for MVP | @pm |
| 2025-01-15 | Grooming - updated priorities | @team |

---

*Document Version: 1.0*
*Template: backlog-template.md*
