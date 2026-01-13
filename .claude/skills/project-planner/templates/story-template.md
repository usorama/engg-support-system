# User Story: [Story Title]

---

## Project Context (MANDATORY FOR AGENTS)

> This section provides critical project-level context for any agent working on this story.

### Working Directory Constraint

**ALL source code MUST be created in the `app/` subdirectory.**

| Content Type  | Correct Location      | NEVER Here    |
| ------------- | --------------------- | ------------- |
| Source files  | `app/src/`            | `src/`        |
| Components    | `app/src/components/` | `components/` |
| API routes    | `app/src/app/api/`    | `api/`        |
| Types         | `app/src/types/`      | `types/`      |
| Hooks         | `app/src/hooks/`      | `hooks/`      |
| Config        | `app/src/config/`     | `config/`     |
| Tests         | `app/src/test/`       | `test/`       |
| Public assets | `app/public/`         | `public/`     |
| Prisma        | `app/prisma/`         | `prisma/`     |

### Command Execution

```bash
# ALWAYS run commands from app/ directory
cd /Users/umasankr/Projects/pinglearn-PWA/app

# Quality gates
pnpm typecheck && pnpm lint && pnpm test
```

### Key Project Files

| File                                   | Purpose                             |
| -------------------------------------- | ----------------------------------- |
| `CLAUDE.md`                            | Project rules and business outcomes |
| `.ai/PROGRESS.md`                      | Current progress and blockers       |
| `docs/planning/IMPLEMENTATION_PLAN.md` | Execution plan                      |

---

## Story Overview

| Field            | Value                                          |
| ---------------- | ---------------------------------------------- |
| **Story ID**     | US-XXX                                         |
| **Epic**         | [E-XXX: Epic Title](link-to-epic)              |
| **Priority**     | Critical / High / Medium / Low                 |
| **Complexity**   | XS / S / M / L / XL                            |
| **Story Points** | [Points]                                       |
| **Sprint**       | [Sprint number or Backlog]                     |
| **Status**       | Draft / Ready / In Progress / In Review / Done |
| **Owner**        | [Developer Name]                               |
| **Created Date** | YYYY-MM-DD                                     |
| **Last Updated** | YYYY-MM-DD                                     |

---

## 1. User Story

### 1.1 Story Statement

> **As a** [persona/user type],
> **I want to** [action/capability],
> **So that** [benefit/value].

### 1.2 Context

[Additional context about when and why this story is relevant. What situation triggers the need for this capability?]

### 1.3 User Persona

| Attribute      | Description                                |
| -------------- | ------------------------------------------ |
| **Persona**    | [Persona name]                             |
| **Role**       | [Their role or job]                        |
| **Goal**       | [What they're trying to achieve]           |
| **Pain Point** | [Current frustration this story addresses] |

---

## 2. Acceptance Criteria

### 2.1 Feature Specification (Gherkin Format)

```gherkin
Feature: [Feature Name]
  As a [persona]
  I want to [capability]
  So that [benefit]

  Background:
    Given [common preconditions for all scenarios]
    And [additional common setup if needed]

  # ============================================
  # Happy Path Scenarios
  # ============================================

  @happy-path @smoke
  Scenario: [Scenario Name - Primary Success Case]
    Given [initial context/state]
    And [additional preconditions if needed]
    When [user action/trigger]
    And [additional actions if needed]
    Then [expected outcome]
    And [additional verifications]

  @happy-path
  Scenario: [Scenario Name - Alternative Success Case]
    Given [initial context/state]
    When [user action/trigger]
    Then [expected outcome]

  # ============================================
  # Edge Cases
  # ============================================

  @edge-case
  Scenario: [Scenario Name - Boundary Condition]
    Given [boundary condition setup]
    When [action at boundary]
    Then [expected behavior at boundary]

  @edge-case
  Scenario: [Scenario Name - Empty State]
    Given [empty or minimal state]
    When [user action]
    Then [graceful handling of empty state]

  # ============================================
  # Error Handling
  # ============================================

  @error-handling
  Scenario: [Scenario Name - Validation Error]
    Given [precondition]
    When [user provides invalid input]
    Then [user sees appropriate error message]
    And [user can correct the error]
    And [no data is corrupted]

  @error-handling
  Scenario: [Scenario Name - System Error]
    Given [precondition]
    And [backend service is unavailable]
    When [user attempts action]
    Then [user sees friendly error message]
    And [user is given retry option or alternative]

  @error-handling
  Scenario: [Scenario Name - Permission Denied]
    Given [user without required permissions]
    When [user attempts restricted action]
    Then [user sees permission denied message]
    And [user is directed to appropriate next step]

  # ============================================
  # Data Variations (Scenario Outline)
  # ============================================

  @data-variations
  Scenario Outline: [Action] with different [data type]
    Given [precondition]
    When user enters "<input>" in the <field> field
    Then the result should be "<expected_result>"

    Examples:
      | input | field | expected_result |
      | valid_value_1 | field_name | success_message |
      | valid_value_2 | field_name | success_message |
      | invalid_value | field_name | error_message |
      | boundary_value | field_name | appropriate_result |
```

### 2.2 Acceptance Criteria Checklist

**Functional Requirements:**

- [ ] [Criterion 1: Specific, testable requirement]
- [ ] [Criterion 2: Specific, testable requirement]
- [ ] [Criterion 3: Specific, testable requirement]

**UI/UX Requirements:**

- [ ] [UI matches approved designs/wireframes]
- [ ] [Loading states are displayed during async operations]
- [ ] [Error states provide clear, actionable feedback]
- [ ] [Success states confirm completed actions]

**Accessibility Requirements:**

- [ ] [All interactive elements are keyboard accessible]
- [ ] [Screen reader announces state changes]
- [ ] [Color contrast meets WCAG 2.1 AA standards]
- [ ] [Focus management is logical and visible]

**Performance Requirements:**

- [ ] [Page loads in < X seconds]
- [ ] [Action completes in < X seconds]
- [ ] [No unnecessary re-renders or API calls]

---

## 3. Technical Notes

### 3.1 Implementation Approach

[High-level technical approach. How should this be implemented?]

### 3.2 Components Affected

| Component          | Type                      | Changes Required         |
| ------------------ | ------------------------- | ------------------------ |
| [Component/File 1] | Frontend/Backend/Database | [Description of changes] |
| [Component/File 2] | Frontend/Backend/Database | [Description of changes] |
| [Component/File 3] | Frontend/Backend/Database | [Description of changes] |

### 3.3 API Changes

**New Endpoints:**

| Method          | Endpoint             | Description    |
| --------------- | -------------------- | -------------- |
| [POST/GET/etc.] | `/api/v1/[endpoint]` | [What it does] |

**Modified Endpoints:**

| Method   | Endpoint             | Changes        |
| -------- | -------------------- | -------------- |
| [Method] | `/api/v1/[endpoint]` | [What changes] |

### 3.4 Database Changes

| Table        | Change Type      | Description    |
| ------------ | ---------------- | -------------- |
| [Table name] | New/Modify/Index | [What changes] |

**Migration Required:** Yes / No
**Migration Script:** [Link if applicable]

### 3.5 Third-Party Dependencies

| Dependency    | Purpose      | Version   | Documentation |
| ------------- | ------------ | --------- | ------------- |
| [Library/API] | [Why needed] | [Version] | [Link]        |

### 3.6 Feature Flags

| Flag Name   | Purpose            | Default State    |
| ----------- | ------------------ | ---------------- |
| [flag_name] | [What it controls] | Enabled/Disabled |

### 3.7 Technical Risks

| Risk             | Impact            | Mitigation        |
| ---------------- | ----------------- | ----------------- |
| [Technical risk] | [Impact on story] | [How to mitigate] |

---

## 4. Dependencies

### 4.1 Blocked By

| Item         | Type                | Status   | Owner   | ETA   |
| ------------ | ------------------- | -------- | ------- | ----- |
| [Dependency] | Story/Task/External | [Status] | [Owner] | [ETA] |

### 4.2 Blocks

| Item             | Type       | Impact if Delayed |
| ---------------- | ---------- | ----------------- |
| [Dependent item] | Story/Task | [Impact]          |

### 4.3 Related Stories

| Story ID | Relationship | Description             |
| -------- | ------------ | ----------------------- |
| US-XXX   | Related to   | [Why related]           |
| US-XXX   | Follows from | [Sequence relationship] |

---

## 5. Tasks

### 5.1 Implementation Tasks

- [ ] **[Task 1]**: [Description] (@developer, X hours)
- [ ] **[Task 2]**: [Description] (@developer, X hours)
- [ ] **[Task 3]**: [Description] (@developer, X hours)
- [ ] **[Task 4]**: [Description] (@developer, X hours)

### 5.2 Testing Tasks

- [ ] **Write unit tests**: [Components to test] (@developer, X hours)
- [ ] **Write integration tests**: [Flows to test] (@developer, X hours)
- [ ] **Write E2E tests**: [Scenarios to cover] (@qa, X hours)
- [ ] **Manual QA testing**: [Specific test cases] (@qa, X hours)

### 5.3 Documentation Tasks

- [ ] **Update API documentation**: [What to document] (@developer, X hours)
- [ ] **Update user documentation**: [What to document] (@tech-writer, X hours)
- [ ] **Update runbook**: [What to add] (@developer, X hours)

### 5.4 Time Estimate

| Category      | Estimated Hours |
| ------------- | --------------- |
| Development   | [X] hours       |
| Testing       | [X] hours       |
| Documentation | [X] hours       |
| Code Review   | [X] hours       |
| **Total**     | **[X] hours**   |

---

## 6. Test Scenarios

### 6.1 Unit Tests

| Test Case     | Component   | Expected Result   |
| ------------- | ----------- | ----------------- |
| [Test case 1] | [Component] | [Expected result] |
| [Test case 2] | [Component] | [Expected result] |
| [Test case 3] | [Component] | [Expected result] |

### 6.2 Integration Tests

| Test Case     | Systems Involved         | Expected Result   |
| ------------- | ------------------------ | ----------------- |
| [Test case 1] | [API + Database]         | [Expected result] |
| [Test case 2] | [Service + External API] | [Expected result] |

### 6.3 End-to-End Tests

| Test Scenario | Steps                         | Expected Outcome   |
| ------------- | ----------------------------- | ------------------ |
| [Scenario 1]  | 1. [Step] 2. [Step] 3. [Step] | [Expected outcome] |
| [Scenario 2]  | 1. [Step] 2. [Step] 3. [Step] | [Expected outcome] |

### 6.4 Manual Test Cases

| Test ID | Test Case        | Preconditions  | Steps              | Expected Result   | Priority |
| ------- | ---------------- | -------------- | ------------------ | ----------------- | -------- |
| TC-001  | [Test case name] | [Setup needed] | [Steps to execute] | [Expected result] | High     |
| TC-002  | [Test case name] | [Setup needed] | [Steps to execute] | [Expected result] | Medium   |

### 6.5 Edge Cases to Test

| Edge Case     | Why Important      | Expected Behavior          |
| ------------- | ------------------ | -------------------------- |
| [Edge case 1] | [Why this matters] | [How system should behave] |
| [Edge case 2] | [Why this matters] | [How system should behave] |

### 6.6 Performance Tests

| Scenario   | Load                 | Expected Response Time | Threshold |
| ---------- | -------------------- | ---------------------- | --------- |
| [Scenario] | [X concurrent users] | < [X] ms               | P95       |

---

## 7. Design Assets

### 7.1 Wireframes/Mockups

| Asset            | Description     | Link         | Status             |
| ---------------- | --------------- | ------------ | ------------------ |
| [Wireframe name] | [What it shows] | [Figma/Link] | Approved/In Review |
| [Mockup name]    | [What it shows] | [Figma/Link] | Approved/In Review |

### 7.2 Design Specifications

| Element    | Specification          |
| ---------- | ---------------------- |
| Colors     | [Color codes used]     |
| Typography | [Fonts, sizes]         |
| Spacing    | [Margin/padding specs] |
| Animations | [Animation details]    |

### 7.3 Responsive Breakpoints

| Breakpoint | Width          | Key Changes      |
| ---------- | -------------- | ---------------- |
| Mobile     | < 768px        | [Layout changes] |
| Tablet     | 768px - 1024px | [Layout changes] |
| Desktop    | > 1024px       | [Layout changes] |

---

## 8. Definition of Done

### 8.1 Development Checklist

- [ ] Code implemented according to acceptance criteria
- [ ] Code follows team coding standards and style guide
- [ ] Self-review completed (no TODOs, console.logs, etc.)
- [ ] Unit tests written and passing (coverage > 80%)
- [ ] Integration tests written and passing
- [ ] No new linting errors or warnings
- [ ] No TypeScript errors
- [ ] No new security vulnerabilities introduced
- [ ] Feature flag configured (if applicable)

### 8.2 Review Checklist

- [ ] Code review completed by at least one peer
- [ ] All code review comments addressed
- [ ] Design review completed (if UI changes)
- [ ] Accessibility review passed

### 8.3 Testing Checklist

- [ ] All automated tests passing in CI
- [ ] Manual QA testing completed
- [ ] Edge cases tested
- [ ] Cross-browser testing completed (if applicable)
- [ ] Mobile/responsive testing completed (if applicable)
- [ ] Performance meets requirements

### 8.4 Documentation Checklist

- [ ] Code comments added for complex logic
- [ ] API documentation updated (if applicable)
- [ ] README updated (if applicable)
- [ ] User documentation updated (if applicable)

### 8.5 Deployment Checklist

- [ ] Changes deployed to staging environment
- [ ] Smoke tests pass in staging
- [ ] Stakeholder/PO review completed in staging
- [ ] Ready for production deployment

---

## 9. Notes & Comments

### 9.1 Implementation Notes

[Any additional notes for the developer implementing this story]

### 9.2 Questions/Clarifications

| Question   | Asked By | Date       | Answer   | Answered By |
| ---------- | -------- | ---------- | -------- | ----------- |
| [Question] | [Name]   | YYYY-MM-DD | [Answer] | [Name]      |

### 9.3 Out of Scope (for this story)

- [Item explicitly not included in this story]
- [Item that was considered but deferred]

---

## 10. History

### 10.1 Status Changes

| Date       | From Status | To Status   | Changed By | Notes                     |
| ---------- | ----------- | ----------- | ---------- | ------------------------- |
| YYYY-MM-DD | Draft       | Ready       | [Name]     | Initial grooming complete |
| YYYY-MM-DD | Ready       | In Progress | [Name]     | Sprint started            |

### 10.2 Revision History

| Date       | Change                      | Author |
| ---------- | --------------------------- | ------ |
| YYYY-MM-DD | Initial story creation      | [Name] |
| YYYY-MM-DD | Updated acceptance criteria | [Name] |
| YYYY-MM-DD | Added technical notes       | [Name] |

---

## Attachments

| Name              | Type                   | Link   |
| ----------------- | ---------------------- | ------ |
| [Attachment name] | [Design/Document/etc.] | [Link] |

---

_This user story document should be updated throughout the development process. Any changes to scope or acceptance criteria should be documented and communicated to stakeholders._
