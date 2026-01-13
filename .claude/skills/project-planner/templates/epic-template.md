# Epic: [Epic Title]

---

## Epic Overview

| Field | Value |
|-------|-------|
| **Epic ID** | E-XXX |
| **Epic Title** | [Descriptive title] |
| **Product Area** | [Feature area or domain] |
| **Owner** | [Product Owner Name] |
| **Created Date** | YYYY-MM-DD |
| **Target Release** | [Release version or date] |
| **Status** | Draft / Ready / In Progress / Done |
| **Priority** | Critical / High / Medium / Low |

---

## 1. Business Goal

### 1.1 Objective
[One clear statement of what this epic aims to achieve from a business perspective.]

### 1.2 Problem Statement
[What problem are we solving? Why is this important now?]

### 1.3 Value Proposition
[How will users and the business benefit from this epic being completed?]

| Stakeholder | Value Delivered |
|-------------|-----------------|
| End Users | [Benefit to users] |
| Business | [Benefit to business] |
| Technical | [Technical improvements] |

### 1.4 Strategic Alignment
[How does this epic align with company/product strategy?]

| Strategic Goal | Contribution |
|----------------|--------------|
| [Goal 1] | [How this epic contributes] |
| [Goal 2] | [How this epic contributes] |

---

## 2. Success Criteria

### 2.1 Business Success Criteria
- [ ] [Measurable business outcome 1]
- [ ] [Measurable business outcome 2]
- [ ] [Measurable business outcome 3]

### 2.2 User Success Criteria
- [ ] [User-focused success metric 1]
- [ ] [User-focused success metric 2]

### 2.3 Technical Success Criteria
- [ ] [Technical requirement 1]
- [ ] [Technical requirement 2]
- [ ] [Performance target]
- [ ] [Quality target]

### 2.4 Key Results

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| [Metric 1] | [Current value] | [Target value] | [How to measure] |
| [Metric 2] | [Current value] | [Target value] | [How to measure] |
| [Metric 3] | [Current value] | [Target value] | [How to measure] |

---

## 3. User Stories Summary

### 3.1 Stories Overview

| Story ID | Story Title | Priority | Complexity | Status | Sprint |
|----------|-------------|----------|------------|--------|--------|
| US-001 | [Story title] | High | M | Ready | Sprint 1 |
| US-002 | [Story title] | High | L | Ready | Sprint 1 |
| US-003 | [Story title] | Medium | S | Draft | Sprint 2 |
| US-004 | [Story title] | Medium | M | Draft | Sprint 2 |
| US-005 | [Story title] | Low | S | Draft | Backlog |

### 3.2 Story Groupings

**Phase 1: Foundation** (Must complete first)
| Story ID | Title | Dependencies |
|----------|-------|--------------|
| US-001 | [Title] | None |
| US-002 | [Title] | US-001 |

**Phase 2: Core Features**
| Story ID | Title | Dependencies |
|----------|-------|--------------|
| US-003 | [Title] | US-002 |
| US-004 | [Title] | US-002 |

**Phase 3: Enhancement**
| Story ID | Title | Dependencies |
|----------|-------|--------------|
| US-005 | [Title] | US-003, US-004 |

### 3.3 Story Map

```
User Goals:     [Goal A]                    [Goal B]
                    │                           │
                    ▼                           ▼
Activities:    [Activity 1]              [Activity 2]
                │       │                    │
                ▼       ▼                    ▼
Tasks:      [US-001] [US-002]            [US-003]
            [US-004]                      [US-005]
```

---

## 4. Dependencies

### 4.1 This Epic Depends On

| Dependency | Type | Status | Owner | Impact if Delayed |
|------------|------|--------|-------|-------------------|
| [Epic/Story/System] | Internal/External | Complete/In Progress/Not Started | [Owner] | [Impact description] |
| [Epic/Story/System] | Internal/External | Complete/In Progress/Not Started | [Owner] | [Impact description] |

### 4.2 This Epic Blocks

| Blocked Item | Type | Impact | Notification Plan |
|--------------|------|--------|-------------------|
| [Epic/Story/System] | Internal/External | [Impact if this epic delays] | [How we'll notify] |
| [Epic/Story/System] | Internal/External | [Impact if this epic delays] | [How we'll notify] |

### 4.3 Dependency Visualization

```
┌─────────────────┐
│   Prereq Epic   │
│     E-XXX       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   THIS EPIC     │────▶│  Dependent Epic │
│     E-XXX       │     │     E-XXX       │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  External API   │
│   Integration   │
└─────────────────┘
```

---

## 5. Technical Considerations

### 5.1 Architecture Impact

| Area | Impact | Description |
|------|--------|-------------|
| Frontend | High/Medium/Low/None | [Description of changes] |
| Backend | High/Medium/Low/None | [Description of changes] |
| Database | High/Medium/Low/None | [Schema changes, migrations] |
| Infrastructure | High/Medium/Low/None | [New services, scaling] |
| Third-party | High/Medium/Low/None | [New integrations] |

### 5.2 Technical Decisions Required

| Decision | Options | Recommendation | Status |
|----------|---------|----------------|--------|
| [Decision 1] | [Option A, B, C] | [Recommendation] | Pending/Made |
| [Decision 2] | [Option A, B, C] | [Recommendation] | Pending/Made |

### 5.3 Technical Debt Considerations

| Technical Debt | Impact on Epic | Plan |
|----------------|----------------|------|
| [Existing debt] | [How it affects this work] | [Address now/later] |

### 5.4 Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Performance | [Target metric] | [How to verify] |
| Scalability | [Target capacity] | [How to verify] |
| Security | [Requirements] | [How to verify] |
| Accessibility | [Standard] | [How to verify] |

---

## 6. Risks

### 6.1 Risk Register

| Risk ID | Risk Description | Probability | Impact | Risk Score | Mitigation | Owner |
|---------|------------------|-------------|--------|------------|------------|-------|
| R-001 | [Description] | High/Med/Low | High/Med/Low | [H/M/L] | [Mitigation plan] | [Name] |
| R-002 | [Description] | High/Med/Low | High/Med/Low | [H/M/L] | [Mitigation plan] | [Name] |
| R-003 | [Description] | High/Med/Low | High/Med/Low | [H/M/L] | [Mitigation plan] | [Name] |

### 6.2 Assumptions

| Assumption | Impact if Wrong | Validation Method |
|------------|-----------------|-------------------|
| [Assumption 1] | [Impact] | [How to validate] |
| [Assumption 2] | [Impact] | [How to validate] |

### 6.3 Constraints

| Constraint | Type | Impact |
|------------|------|--------|
| [Constraint 1] | Technical/Business/Time | [How it limits us] |
| [Constraint 2] | Technical/Business/Time | [How it limits us] |

---

## 7. Scope

### 7.1 In Scope
- [Feature/Capability 1]
- [Feature/Capability 2]
- [Feature/Capability 3]
- [Technical improvement 1]

### 7.2 Out of Scope
| Item | Reason | Future Consideration |
|------|--------|---------------------|
| [Item 1] | [Why excluded] | Phase 2 / Never / TBD |
| [Item 2] | [Why excluded] | Phase 2 / Never / TBD |

### 7.3 Open Questions

| Question | Owner | Due Date | Status | Answer |
|----------|-------|----------|--------|--------|
| [Question 1] | [Name] | YYYY-MM-DD | Open/Resolved | [Answer if resolved] |
| [Question 2] | [Name] | YYYY-MM-DD | Open/Resolved | [Answer if resolved] |

---

## 8. Timeline

### 8.1 High-Level Schedule

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Epic Ready for Development | YYYY-MM-DD | [Status] |
| Phase 1 Complete | YYYY-MM-DD | [Status] |
| Phase 2 Complete | YYYY-MM-DD | [Status] |
| Epic Complete | YYYY-MM-DD | [Status] |
| Release to Production | YYYY-MM-DD | [Status] |

### 8.2 Sprint Allocation

| Sprint | Stories | Story Points | Focus |
|--------|---------|--------------|-------|
| Sprint 1 | US-001, US-002 | [Points] | Foundation |
| Sprint 2 | US-003, US-004 | [Points] | Core features |
| Sprint 3 | US-005, Bug fixes | [Points] | Enhancement |

---

## 9. Team & Resources

### 9.1 Team Allocation

| Role | Person | Allocation | Notes |
|------|--------|------------|-------|
| Product Owner | [Name] | [%] | Decision maker |
| Tech Lead | [Name] | [%] | Architecture decisions |
| Frontend Developer | [Name] | [%] | |
| Backend Developer | [Name] | [%] | |
| QA Engineer | [Name] | [%] | |
| Designer | [Name] | [%] | |

### 9.2 External Resources

| Resource | Provider | Purpose | Status |
|----------|----------|---------|--------|
| [Resource 1] | [Provider] | [Purpose] | Secured/Pending |

---

## 10. Definition of Done

### 10.1 Epic-Level DoD

- [ ] All user stories completed and meet their individual DoD
- [ ] All acceptance criteria verified and passing
- [ ] End-to-end integration testing complete
- [ ] Performance requirements met and verified
- [ ] Security review passed
- [ ] Accessibility requirements met (WCAG 2.1 AA)
- [ ] Documentation updated (user docs, API docs, runbooks)
- [ ] Feature flags configured (if applicable)
- [ ] Monitoring and alerting configured
- [ ] Stakeholder demo completed
- [ ] Product Owner acceptance received
- [ ] Deployed to production (or ready for deployment)
- [ ] Success metrics baseline captured

### 10.2 Quality Gates

| Gate | Criteria | Verification |
|------|----------|--------------|
| Code Quality | All tests pass, coverage > 80% | CI pipeline |
| Security | No critical/high vulnerabilities | Security scan |
| Performance | Meets defined SLAs | Load testing |
| Accessibility | WCAG 2.1 AA compliant | Accessibility audit |
| Documentation | All docs updated | Review checklist |

---

## 11. Release & Rollout

### 11.1 Release Strategy

| Phase | Description | Duration | Success Criteria |
|-------|-------------|----------|------------------|
| Internal Testing | Team and stakeholders | 1 week | All tests pass |
| Beta | [X]% of users | 2 weeks | Error rate < 1% |
| GA | 100% of users | Ongoing | Meet KPIs |

### 11.2 Rollback Plan

| Trigger | Action | Owner | Time to Execute |
|---------|--------|-------|-----------------|
| [Condition for rollback] | [Rollback steps] | [Owner] | [Time] |

### 11.3 Communication Plan

| Audience | Message | Channel | Timing |
|----------|---------|---------|--------|
| Internal Team | Feature complete | Slack | On completion |
| Stakeholders | Release notes | Email | Pre-release |
| End Users | Feature announcement | In-app/Email | On release |

---

## 12. Appendix

### A. Related Documents

| Document | Purpose | Link |
|----------|---------|------|
| PRD | Product requirements | [Link] |
| Architecture | Technical design | [Link] |
| Design Specs | UI/UX specifications | [Link] |
| Test Plan | QA strategy | [Link] |

### B. Meeting Notes / Decisions

| Date | Topic | Decision | Attendees |
|------|-------|----------|-----------|
| YYYY-MM-DD | [Topic] | [Decision made] | [Names] |

### C. Change Log

| Date | Change | Author |
|------|--------|--------|
| YYYY-MM-DD | Initial epic creation | [Name] |
| YYYY-MM-DD | [Change description] | [Name] |

---

*This epic document should be kept up to date as the work progresses. Status updates should be reflected in the relevant sections.*
