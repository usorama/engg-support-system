# Validation Checklist

Quality validation checklist for project planning artifacts.

---

## 1. PRD Validation

### Completeness
- [ ] Problem statement is clearly defined
- [ ] Target users/personas are identified
- [ ] Success metrics are quantified
- [ ] Scope boundaries are explicit (in-scope and out-of-scope)
- [ ] Assumptions are documented
- [ ] Dependencies are identified
- [ ] Risks are assessed with mitigations
- [ ] Timeline and milestones are included
- [ ] Acceptance criteria are defined

### Clarity
- [ ] Language is unambiguous (no "should", "might", "could")
- [ ] Technical jargon is explained or avoided
- [ ] Requirements use consistent terminology
- [ ] User flows are described step-by-step
- [ ] Edge cases are addressed
- [ ] Error states are defined
- [ ] Priority is clear (MoSCoW or similar)

### Testability
- [ ] Each requirement has measurable acceptance criteria
- [ ] Success metrics have specific targets
- [ ] Test scenarios can be derived from requirements
- [ ] Non-functional requirements have thresholds
- [ ] User acceptance criteria are defined
- [ ] Performance benchmarks are specified

### Stakeholder Alignment
- [ ] All stakeholders have reviewed and approved
- [ ] Conflicting requirements have been resolved
- [ ] Sign-off process is documented
- [ ] Change control process is defined

---

## 2. Architecture Validation

### Soundness
- [ ] Architecture addresses all functional requirements
- [ ] Data flow is clearly documented
- [ ] Component responsibilities are well-defined
- [ ] Interfaces between components are specified
- [ ] Technology choices are justified
- [ ] Patterns used are appropriate for the problem
- [ ] Architecture follows established conventions

### Scalability
- [ ] Horizontal scaling approach is defined
- [ ] Bottlenecks are identified and addressed
- [ ] Caching strategy is documented
- [ ] Database scaling approach is defined
- [ ] Load estimates are realistic
- [ ] Growth projections are considered
- [ ] Auto-scaling policies are defined (if applicable)

### Security
- [ ] Authentication mechanism is defined
- [ ] Authorization model is documented
- [ ] Data encryption approach (at rest and in transit)
- [ ] Secrets management is addressed
- [ ] Input validation strategy is defined
- [ ] Security audit points are identified
- [ ] Compliance requirements are addressed
- [ ] Attack surface is minimized

### Reliability
- [ ] Failure modes are identified
- [ ] Recovery procedures are documented
- [ ] Backup and restore strategy exists
- [ ] Monitoring and alerting is planned
- [ ] SLAs are defined and achievable
- [ ] Circuit breakers and retries are considered
- [ ] Graceful degradation is planned

### Maintainability
- [ ] Code organization follows standards
- [ ] Logging strategy is defined
- [ ] Debugging approach is considered
- [ ] Documentation requirements are specified
- [ ] On-call procedures are planned
- [ ] Deployment rollback is possible

---

## 3. Story Validation

### INVEST Criteria
- [ ] **Independent**: Can be developed and delivered separately
- [ ] **Negotiable**: Details can be refined during development
- [ ] **Valuable**: Delivers value to user or business
- [ ] **Estimable**: Team can estimate effort
- [ ] **Small**: Completable within one sprint
- [ ] **Testable**: Has clear acceptance criteria

### Story Quality
- [ ] User story format is followed (As a... I want... So that...)
- [ ] Acceptance criteria are specific and measurable
- [ ] Definition of Done is applicable
- [ ] Dependencies are identified and linked
- [ ] Priority is assigned
- [ ] Estimate is provided
- [ ] Risks are flagged

### Story Completeness
- [ ] Happy path is described
- [ ] Error scenarios are defined
- [ ] Edge cases are considered
- [ ] UI/UX requirements are specified (if applicable)
- [ ] API contracts are defined (if applicable)
- [ ] Data requirements are clear
- [ ] Security requirements are noted

---

## 4. Task Validation

### Verifiability
- [ ] Task has clear completion criteria
- [ ] Output is tangible and demonstrable
- [ ] Testing approach is defined
- [ ] Review process is specified
- [ ] Definition of Done is applicable

### Dependencies
- [ ] Blocking dependencies are identified
- [ ] Blocked-by relationships are documented
- [ ] External dependencies are flagged
- [ ] Parallel work is identified
- [ ] Critical path is understood

### Sizing
- [ ] Estimate is in appropriate units (hours/points)
- [ ] Estimate accounts for testing time
- [ ] Estimate includes code review time
- [ ] Task is appropriately sized (not too big/small)
- [ ] Uncertainty is reflected in estimate

### Assignment
- [ ] Required skills are identified
- [ ] Appropriate assignee is available
- [ ] Knowledge sharing is considered
- [ ] Backup assignee is identified (if critical)

---

## 5. Sprint Readiness Validation

### Backlog Health
- [ ] All stories are estimated
- [ ] Top stories are refined and ready
- [ ] Dependencies are resolved or scheduled
- [ ] Technical spikes are completed
- [ ] Design assets are available (if needed)
- [ ] API contracts are agreed upon

### Team Readiness
- [ ] Team capacity is calculated
- [ ] Vacation/PTO is accounted for
- [ ] On-call rotation is considered
- [ ] Required skills are available
- [ ] External dependencies are committed

### Sprint Goal
- [ ] Sprint goal is defined and clear
- [ ] Goal aligns with product roadmap
- [ ] Stories support the sprint goal
- [ ] Goal is achievable within sprint
- [ ] Team is aligned on goal

---

## Usage Guidelines

### When to Use This Checklist

| Artifact | Validation Timing |
|----------|-------------------|
| PRD | Before development kickoff |
| Architecture | Before implementation begins |
| Stories | During backlog refinement |
| Tasks | During sprint planning |
| Sprint | Before sprint commitment |

### Validation Process

1. **Self-Review**: Author validates against checklist
2. **Peer Review**: Another team member validates
3. **Stakeholder Review**: Key stakeholders validate
4. **Document Gaps**: Record items that don't pass
5. **Remediate**: Address gaps before proceeding
6. **Final Sign-off**: Get explicit approval

### Red Flags

- More than 20% of checklist items failing
- Critical items (security, testability) failing
- Repeated failures in same category
- Resistance to validation process
- "We'll figure it out later" responses
