# Definition of Done Templates

Templates for Definition of Done (DoD) at various levels of work.

---

## Overview

Definition of Done is a shared understanding of what it means for work to be complete. It ensures quality and consistency across the team.

### DoD Levels

```
Story DoD     → Individual user stories
Sprint DoD    → Sprint completion criteria
Epic DoD      → Large feature completion
Release DoD   → Production release criteria
```

---

## 1. Story Definition of Done

### Code Quality
- [ ] Code compiles without errors
- [ ] Code passes all linting rules
- [ ] Code follows project coding standards
- [ ] No TODO comments left in code (or tracked in backlog)
- [ ] No console.log or debug statements in production code
- [ ] TypeScript strict mode passes (0 errors)

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing (if applicable)
- [ ] Test coverage meets minimum threshold (≥80%)
- [ ] Edge cases are tested
- [ ] Error scenarios are tested
- [ ] Manual testing completed by developer

### Code Review
- [ ] Pull request created with description
- [ ] Code review completed by at least one peer
- [ ] Review feedback addressed
- [ ] PR approved by required reviewers
- [ ] No unresolved review comments

### Documentation
- [ ] Code is self-documenting (clear names, structure)
- [ ] Complex logic has inline comments
- [ ] API documentation updated (if applicable)
- [ ] README updated (if applicable)
- [ ] Change documented in changelog (if applicable)

### Acceptance Criteria
- [ ] All acceptance criteria verified
- [ ] Demo-able to product owner
- [ ] Product owner has accepted the story
- [ ] Works in all supported browsers/platforms
- [ ] Responsive design verified (if applicable)

### Deployment
- [ ] Code merged to main/development branch
- [ ] CI/CD pipeline passes
- [ ] Deployed to staging environment
- [ ] Smoke tested in staging
- [ ] Feature flag configured (if applicable)

### Story DoD Checklist Template

```markdown
## Story: [STORY-###] [Title]

### Code Quality
- [ ] Compiles without errors
- [ ] Linting passes
- [ ] Coding standards followed
- [ ] No debug statements

### Testing
- [ ] Unit tests passing
- [ ] Coverage ≥80%
- [ ] Edge cases tested
- [ ] Manual testing done

### Review
- [ ] PR created
- [ ] Code review passed
- [ ] PR approved

### Acceptance
- [ ] All AC verified
- [ ] PO accepted
- [ ] Cross-browser tested

### Deployment
- [ ] Merged to main
- [ ] CI/CD passed
- [ ] Deployed to staging
- [ ] Smoke tested

**Status**: [ ] DONE / [ ] NOT DONE
```

---

## 2. Sprint Definition of Done

### Story Completion
- [ ] All committed stories meet Story DoD
- [ ] All stories are accepted by Product Owner
- [ ] No stories are partially complete
- [ ] Sprint goal is achieved

### Quality Metrics
- [ ] Overall test coverage ≥80%
- [ ] No critical bugs open
- [ ] No high-severity bugs introduced
- [ ] Performance benchmarks met
- [ ] Security scan passed

### Integration
- [ ] All stories are integrated together
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] No regression in existing functionality
- [ ] API contracts are honored

### Documentation
- [ ] Sprint documentation updated
- [ ] Release notes drafted
- [ ] Technical documentation updated
- [ ] User documentation updated (if user-facing changes)

### Team Activities
- [ ] Sprint retrospective conducted
- [ ] Sprint review/demo completed
- [ ] Next sprint backlog refined
- [ ] Impediments resolved or escalated
- [ ] Metrics collected and reviewed

### Deployment Readiness
- [ ] All code deployed to staging
- [ ] Staging environment is stable
- [ ] Release candidate is tagged
- [ ] Rollback plan is in place

### Sprint DoD Checklist Template

```markdown
## Sprint: [Sprint Name/Number]
## Sprint Goal: [Goal Statement]

### Story Completion
- [ ] All stories meet Story DoD: [X/Y stories]
- [ ] All stories PO accepted
- [ ] Sprint goal achieved

### Quality
- [ ] Test coverage: [XX]%
- [ ] Critical bugs: [0]
- [ ] High bugs: [0]
- [ ] Performance: [Pass/Fail]
- [ ] Security scan: [Pass/Fail]

### Integration
- [ ] Integration tests: [Pass/Fail]
- [ ] E2E tests: [Pass/Fail]
- [ ] Regression: [None detected]

### Documentation
- [ ] Release notes drafted
- [ ] Tech docs updated
- [ ] User docs updated

### Team
- [ ] Retro completed
- [ ] Sprint review completed
- [ ] Next sprint refined

### Deployment
- [ ] Deployed to staging
- [ ] Staging stable
- [ ] Release candidate tagged

**Sprint Status**: [ ] DONE / [ ] NOT DONE
```

---

## 3. Epic Definition of Done

### Scope Completion
- [ ] All in-scope stories completed
- [ ] All acceptance criteria met
- [ ] Out-of-scope items documented for future
- [ ] No deferred items without explicit approval
- [ ] Epic objective achieved

### Quality Standards
- [ ] All stories meet Story DoD
- [ ] End-to-end user flows tested
- [ ] Performance requirements met
- [ ] Security requirements met
- [ ] Accessibility requirements met
- [ ] Cross-browser/platform compatibility verified

### User Validation
- [ ] User acceptance testing completed
- [ ] Usability testing completed (if applicable)
- [ ] Beta testing completed (if applicable)
- [ ] Feedback addressed or documented
- [ ] Success metrics baseline established

### Documentation
- [ ] User documentation complete
- [ ] Training materials created (if applicable)
- [ ] Support documentation updated
- [ ] Architecture documentation updated
- [ ] Runbook/operations guide updated

### Stakeholder Sign-off
- [ ] Product Owner approval
- [ ] Technical Lead approval
- [ ] QA Lead approval
- [ ] Design approval (if applicable)
- [ ] Security approval (if applicable)
- [ ] Stakeholder demo completed

### Release Preparation
- [ ] Feature flag ready for rollout
- [ ] Rollout plan defined
- [ ] Rollback plan defined
- [ ] Monitoring/alerting configured
- [ ] Success metrics tracking configured

### Epic DoD Checklist Template

```markdown
## Epic: [EPIC-###] [Title]
## Objective: [Objective Statement]

### Scope
- [ ] Stories completed: [X/Y]
- [ ] All AC met
- [ ] Deferred items documented
- [ ] Objective achieved

### Quality
- [ ] E2E flows tested
- [ ] Performance: [XX]ms (target: [YY]ms)
- [ ] Security: [Pass]
- [ ] Accessibility: [WCAG level]
- [ ] Browser compatibility: [Pass]

### Validation
- [ ] UAT completed
- [ ] Usability testing done
- [ ] Feedback addressed
- [ ] Metrics baseline set

### Documentation
- [ ] User docs complete
- [ ] Training materials ready
- [ ] Support docs updated
- [ ] Architecture docs updated
- [ ] Runbook updated

### Sign-off
- [ ] Product Owner: [Name] [Date]
- [ ] Tech Lead: [Name] [Date]
- [ ] QA Lead: [Name] [Date]
- [ ] Design: [Name] [Date]

### Release
- [ ] Feature flag ready
- [ ] Rollout plan defined
- [ ] Rollback plan defined
- [ ] Monitoring configured
- [ ] Metrics tracking configured

**Epic Status**: [ ] DONE / [ ] NOT DONE
```

---

## 4. Release Definition of Done

### Feature Completion
- [ ] All release-scoped epics complete
- [ ] All release-scoped features meet Epic DoD
- [ ] Release scope has not changed without approval
- [ ] All deferred items are documented

### Quality Assurance
- [ ] Full regression test suite passed
- [ ] Performance testing completed and approved
- [ ] Security testing completed and approved
- [ ] Penetration testing completed (if applicable)
- [ ] Load testing completed and approved
- [ ] Accessibility audit passed
- [ ] No critical or high-severity bugs

### Compliance
- [ ] Legal review completed (if applicable)
- [ ] Compliance review completed (if applicable)
- [ ] Privacy review completed (if applicable)
- [ ] Licensing review completed
- [ ] Audit trail requirements met

### Operations Readiness
- [ ] Production environment prepared
- [ ] Infrastructure scaled appropriately
- [ ] Monitoring and alerting configured
- [ ] Logging configured and tested
- [ ] Runbooks created/updated
- [ ] On-call team briefed
- [ ] Support team trained

### Documentation
- [ ] Release notes finalized
- [ ] User documentation published
- [ ] API documentation published
- [ ] Migration guide created (if applicable)
- [ ] Known issues documented
- [ ] Changelog updated

### Communication
- [ ] Internal stakeholders notified
- [ ] Marketing materials prepared (if applicable)
- [ ] Customer communication prepared (if applicable)
- [ ] Support team briefed
- [ ] Sales team briefed (if applicable)

### Deployment
- [ ] Deployment plan documented
- [ ] Rollback plan documented and tested
- [ ] Database migration tested
- [ ] Data backup completed
- [ ] Deployment approved by release manager
- [ ] Change management ticket approved

### Post-Release
- [ ] Success metrics defined
- [ ] Monitoring dashboard configured
- [ ] Hotfix process documented
- [ ] Post-release review scheduled

### Release DoD Checklist Template

```markdown
## Release: [Version Number]
## Release Date: [Date]
## Release Type: [Major/Minor/Patch]

### Features
- [ ] Epics completed: [X/Y]
- [ ] All features meet Epic DoD
- [ ] Scope approved
- [ ] Deferred items documented

### Quality
- [ ] Regression tests: [Pass]
- [ ] Performance tests: [Pass]
- [ ] Security tests: [Pass]
- [ ] Load tests: [Pass]
- [ ] Accessibility: [Pass]
- [ ] Critical bugs: [0]
- [ ] High bugs: [0]

### Compliance
- [ ] Legal review: [Pass/NA]
- [ ] Compliance review: [Pass/NA]
- [ ] Privacy review: [Pass/NA]

### Operations
- [ ] Production environment ready
- [ ] Monitoring configured
- [ ] Runbooks updated
- [ ] On-call briefed
- [ ] Support trained

### Documentation
- [ ] Release notes: [Link]
- [ ] User docs: [Link]
- [ ] API docs: [Link]
- [ ] Known issues: [Link]

### Communication
- [ ] Internal announcement: [Sent]
- [ ] Customer communication: [Sent/NA]
- [ ] Support briefed: [Done]

### Deployment
- [ ] Deployment plan: [Link]
- [ ] Rollback plan: [Link]
- [ ] Backup completed: [Done]
- [ ] Change ticket: [CM-###]

### Approvals
- [ ] Release Manager: [Name] [Date]
- [ ] Engineering Lead: [Name] [Date]
- [ ] Product Lead: [Name] [Date]
- [ ] QA Lead: [Name] [Date]
- [ ] Ops Lead: [Name] [Date]

**Release Status**: [ ] READY FOR RELEASE / [ ] NOT READY
```

---

## Customization Guidelines

### Tailoring DoD to Your Project

1. **Start minimal**: Begin with essential items, add as needed
2. **Team agreement**: DoD should be agreed upon by the whole team
3. **Review regularly**: Update DoD based on retrospectives
4. **Make it visible**: Post DoD in team workspace
5. **Enforce consistently**: DoD is non-negotiable once agreed

### DoD Maturity Levels

| Level | Characteristics |
|-------|-----------------|
| **Basic** | Code compiles, tests pass, code reviewed |
| **Intermediate** | + Coverage thresholds, documentation, deployment |
| **Advanced** | + Security, performance, accessibility, compliance |
| **Mature** | + Metrics, monitoring, operational readiness |

### Red Flags

- Bypassing DoD for deadlines (leads to tech debt)
- DoD items that are never checked (remove or enforce)
- DoD that's too long (becomes ignored)
- DoD that varies by person (inconsistent quality)
- No DoD enforcement mechanism (becomes theater)
