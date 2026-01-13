# Gap Analysis Checklist

Systematic approach to identifying and resolving gaps in project planning.

---

## 1. Requirements Completeness

### User Needs Coverage
- [ ] All identified personas have their needs addressed
- [ ] Primary use cases are fully specified
- [ ] Secondary use cases are documented
- [ ] User journey is complete (no missing steps)
- [ ] Error recovery paths are defined
- [ ] Accessibility requirements are addressed
- [ ] Internationalization needs are considered

### User Story Coverage
- [ ] Every requirement maps to at least one story
- [ ] Stories cover all user roles
- [ ] Stories cover all priority levels
- [ ] Stories are linked to business objectives
- [ ] Orphan requirements are investigated
- [ ] Duplicate/overlapping stories are consolidated

### Non-Functional Requirements (NFRs)
- [ ] Performance requirements are quantified
- [ ] Scalability targets are defined
- [ ] Availability/uptime requirements are specified
- [ ] Security requirements are documented
- [ ] Compliance requirements are identified
- [ ] Data retention requirements are clear
- [ ] Disaster recovery requirements exist
- [ ] Maintainability standards are defined

---

## 2. Architecture Completeness

### Design Coverage
- [ ] All functional requirements have architectural support
- [ ] All NFRs are addressed in architecture
- [ ] Data model supports all use cases
- [ ] API design covers all integrations
- [ ] UI architecture supports all screens/flows
- [ ] Background job architecture is defined
- [ ] Caching strategy covers performance needs

### Technology Stack
- [ ] All required capabilities have technology choices
- [ ] Technology versions are specified
- [ ] License compatibility is verified
- [ ] Team skills match technology choices
- [ ] Technology choices are documented with rationale
- [ ] Alternative options were evaluated
- [ ] Migration path exists for legacy components

### Quality Attributes
- [ ] Security controls are architecturally enforced
- [ ] Observability is built into design
- [ ] Testability is considered in architecture
- [ ] Deployment automation is designed
- [ ] Configuration management is addressed
- [ ] Feature flags/toggles are designed
- [ ] A/B testing capability is considered

---

## 3. Implementation Readiness

### Task Decomposition
- [ ] All stories are broken into tasks
- [ ] Tasks are appropriately sized (1-3 days)
- [ ] Technical tasks are identified (infra, devops)
- [ ] Testing tasks are included
- [ ] Documentation tasks are included
- [ ] Code review time is accounted for
- [ ] Deployment tasks are included

### Prioritization
- [ ] Dependencies are identified and sequenced
- [ ] Critical path is identified
- [ ] Quick wins are identified
- [ ] Risk-reduction work is prioritized
- [ ] Technical debt is prioritized appropriately
- [ ] MVP vs. full scope is clear
- [ ] Iteration boundaries are defined

### Evidence & Validation
- [ ] Assumptions have validation plans
- [ ] Prototypes/spikes have been executed
- [ ] Technical feasibility is confirmed
- [ ] Third-party integrations are tested
- [ ] Performance assumptions are benchmarked
- [ ] Security approach is validated
- [ ] User research supports requirements

---

## 4. Gap Identification

### Gap Discovery Methods

#### Requirements Gaps
| Gap Type | Discovery Method | Owner |
|----------|------------------|-------|
| Missing persona needs | User research review | Product |
| Incomplete user stories | Story mapping exercise | Product/Dev |
| NFR gaps | Architecture review | Tech Lead |
| Edge case gaps | QA review of requirements | QA |

#### Architecture Gaps
| Gap Type | Discovery Method | Owner |
|----------|------------------|-------|
| Missing components | Traceability matrix | Tech Lead |
| Integration gaps | API review | Tech Lead |
| Security gaps | Threat modeling | Security |
| Scalability gaps | Load modeling | Tech Lead |

#### Implementation Gaps
| Gap Type | Discovery Method | Owner |
|----------|------------------|-------|
| Missing tasks | Story refinement | Dev Team |
| Skill gaps | Team skills inventory | Engineering Manager |
| Tool gaps | Development environment review | DevOps |
| Knowledge gaps | Technical spike planning | Tech Lead |

### Gap Documentation Template

```markdown
## Gap ID: [GAP-###]

**Category**: [Requirements | Architecture | Implementation]
**Severity**: [Critical | High | Medium | Low]
**Status**: [Identified | Analyzed | Resolving | Resolved]

### Description
[Clear description of what is missing or incomplete]

### Impact
[What happens if this gap is not addressed]

### Discovery Date
[When was this gap identified]

### Discovered By
[Who identified this gap]

### Root Cause
[Why does this gap exist]

### Resolution
[How will this gap be addressed]

### Owner
[Who is responsible for resolution]

### Target Date
[When should this be resolved]

### Dependencies
[What is blocked by or blocking this gap]
```

---

## 5. Resolution Actions

### Resolution Process

```
1. IDENTIFY → Document gap using template
2. ASSESS → Determine severity and impact
3. PRIORITIZE → Rank against other gaps
4. ASSIGN → Designate owner and target date
5. RESOLVE → Execute resolution plan
6. VERIFY → Confirm gap is closed
7. DOCUMENT → Update project artifacts
```

### Resolution Strategies by Gap Type

#### Requirements Gaps
| Strategy | When to Use |
|----------|-------------|
| User research | Missing user context |
| Stakeholder interview | Missing business context |
| Competitive analysis | Missing industry context |
| Technical spike | Missing feasibility data |
| Assumption documentation | Low-risk unknowns |

#### Architecture Gaps
| Strategy | When to Use |
|----------|-------------|
| Design session | Missing component design |
| Proof of concept | Unvalidated approach |
| Vendor evaluation | Missing technology choice |
| Security review | Missing security controls |
| Architecture decision record | Missing rationale |

#### Implementation Gaps
| Strategy | When to Use |
|----------|-------------|
| Story refinement | Incomplete task breakdown |
| Training/pairing | Team skill gaps |
| Tool procurement | Missing capabilities |
| Documentation creation | Missing knowledge |
| Dependency resolution | Blocked work items |

### Resolution Tracking

```markdown
## Gap Resolution Tracker

| Gap ID | Category | Severity | Owner | Target | Status |
|--------|----------|----------|-------|--------|--------|
| GAP-001 | Req | High | @pm | 01/15 | Resolved |
| GAP-002 | Arch | Critical | @tech | 01/12 | In Progress |
| GAP-003 | Impl | Medium | @dev | 01/20 | Identified |
```

---

## 6. Completeness Verification

### Requirements Completeness Score
- [ ] 100% of personas have documented needs
- [ ] 100% of must-have requirements have stories
- [ ] 100% of NFRs have measurable criteria
- [ ] 0 critical gaps remain open
- [ ] 0 high gaps remain unassigned

### Architecture Completeness Score
- [ ] 100% of requirements have architectural support
- [ ] 100% of technology choices are documented
- [ ] 100% of quality attributes are addressed
- [ ] All architecture decisions are recorded
- [ ] Security review is complete

### Implementation Completeness Score
- [ ] 100% of stories have task breakdown
- [ ] 100% of tasks have estimates
- [ ] 0 blocking dependencies are unresolved
- [ ] All skill gaps have mitigation plans
- [ ] Sprint 1 is fully ready

---

## Usage Guidelines

### When to Perform Gap Analysis

| Milestone | Gap Analysis Focus |
|-----------|-------------------|
| Project kickoff | Requirements completeness |
| Architecture review | Architecture completeness |
| Sprint planning | Implementation readiness |
| Mid-project checkpoint | All areas |
| Pre-release | Quality and compliance |

### Gap Analysis Meeting Format

1. **Preparation** (async): Review artifacts against checklists
2. **Meeting** (60-90 min): Walk through each section, document gaps
3. **Prioritization** (15 min): Rank gaps by severity
4. **Assignment** (15 min): Assign owners and dates
5. **Follow-up** (async): Track resolution progress

### Success Criteria

- All critical gaps resolved before development starts
- All high gaps have resolution plans before development starts
- Gap resolution is tracked in project status
- New gaps are captured continuously
- Gap trends are monitored (decreasing over time)
