# INVEST Criteria for User Stories

A comprehensive guide to validating user stories using INVEST criteria.

---

## Overview

INVEST is an acronym that describes the characteristics of a well-formed user story:

| Letter | Criterion | Question |
|--------|-----------|----------|
| **I** | Independent | Can this be built and delivered on its own? |
| **N** | Negotiable | Can details be refined during development? |
| **V** | Valuable | Does this deliver value to users or business? |
| **E** | Estimable | Can the team estimate the effort required? |
| **S** | Small | Can this be completed in one sprint? |
| **T** | Testable | Can we verify this works as expected? |

---

## I - Independent

### Definition
Stories should be self-contained and not have inherent dependencies on other stories. They can be developed, tested, and delivered in any order.

### Validation Checklist
- [ ] Story can be implemented without waiting for another story
- [ ] Story delivers value even if other stories are delayed
- [ ] Story can be tested in isolation
- [ ] Story can be deployed independently
- [ ] No circular dependencies with other stories

### Example: Good
```
As a user, I want to reset my password via email
so that I can regain access to my account if I forget it.
```
*This story can be built independently of other authentication features.*

### Example: Bad
```
As a user, I want to see my profile page
so that I can view my information.

[Depends on: User registration story, Avatar upload story, Bio editing story]
```
*This story has multiple dependencies and should be split.*

### How to Fix Dependency Issues
1. **Combine stories**: If stories are tightly coupled, combine them
2. **Split differently**: Reorganize to create independent slices
3. **Use stubs/mocks**: Allow development with stubbed dependencies
4. **Vertical slicing**: Slice by user journey, not by technical layer

---

## N - Negotiable

### Definition
Stories are not contracts. They are placeholders for conversations. The specific implementation details should be negotiable and refined during development.

### Validation Checklist
- [ ] Story describes "what" not "how"
- [ ] Implementation approach is not prescribed
- [ ] UI/UX details are flexible (unless critical)
- [ ] Story can be refined based on learnings
- [ ] Scope can be adjusted based on constraints

### Example: Good
```
As a shopper, I want to filter products by price range
so that I can find items within my budget.

Acceptance Criteria:
- User can set minimum and maximum price
- Filtered results update dynamically
- Clear filter option is available
```
*Details of UI (slider vs. inputs) can be negotiated.*

### Example: Bad
```
As a shopper, I want a dual-handle slider with
$10 increments, debounced at 300ms, using the
Material UI Range component positioned below
the category filter on the left sidebar...
```
*Over-specified. No room for negotiation or better solutions.*

### How to Improve Negotiability
1. **Focus on outcomes**: Describe the user goal, not the solution
2. **Use acceptance criteria wisely**: Define what, not how
3. **Leave design space**: Allow for creative solutions
4. **Iterate during development**: Refine as understanding grows

---

## V - Valuable

### Definition
Every story should deliver value to the user or to the business. Technical stories should be reframed to show their value.

### Validation Checklist
- [ ] Story solves a real user problem
- [ ] User benefit is clearly stated ("so that...")
- [ ] Business value can be articulated
- [ ] Stakeholder would pay for this feature
- [ ] Story contributes to product goals

### Example: Good
```
As a content creator, I want to schedule posts in advance
so that I can maintain a consistent posting schedule
without being online at specific times.
```
*Clear user value: time savings and consistency.*

### Example: Bad
```
As a developer, I want to refactor the database layer
so that the code is cleaner.
```
*No user value stated. "Cleaner code" is not a business outcome.*

### Example: Bad Reframed as Good
```
As a content creator, I want the app to load my dashboard
in under 2 seconds so that I can quickly check my metrics
without waiting.

[Technical enabler: Database query optimization]
```
*Technical work framed with user value.*

### How to Ensure Value
1. **Ask "So what?"**: Challenge every story's value
2. **Trace to objectives**: Link to product goals/OKRs
3. **Quantify when possible**: "Save 10 minutes per user per day"
4. **Reframe technical debt**: Express in terms of user impact

---

## E - Estimable

### Definition
The team should be able to estimate the effort required to complete the story. If a story cannot be estimated, it needs more refinement or a spike.

### Validation Checklist
- [ ] Team understands what needs to be built
- [ ] Team has built similar things before (or done a spike)
- [ ] Technical approach is reasonably clear
- [ ] Major unknowns have been identified
- [ ] Story is not so large that estimation is meaningless

### Example: Good
```
As a user, I want to export my data as a CSV file
so that I can analyze it in a spreadsheet.

Team estimate: 3 story points
Rationale: Similar to PDF export we built last sprint
```
*Team has experience and can estimate confidently.*

### Example: Bad
```
As a user, I want AI-powered recommendations
so that I can discover relevant content.

Team estimate: ???
"We've never done ML before and don't know what's involved."
```
*Cannot estimate due to unknowns.*

### How to Make Stories Estimable
1. **Spike first**: Time-boxed research before estimation
2. **Break down**: Smaller stories are easier to estimate
3. **Reference past work**: Compare to similar completed stories
4. **Identify unknowns**: Make uncertainty explicit
5. **Accept ranges**: Use t-shirt sizes for uncertain stories

---

## S - Small

### Definition
Stories should be small enough to be completed within a single sprint/iteration. Ideally, multiple stories can be completed per sprint.

### Validation Checklist
- [ ] Story can be completed in 1-5 days of work
- [ ] Story fits comfortably within a sprint
- [ ] Story is not an epic in disguise
- [ ] Story has a focused, single objective
- [ ] Story doesn't require multiple developers for weeks

### Example: Good
```
As a user, I want to add a profile photo
so that other users can recognize me.

Estimate: 2 days
```
*Focused, completable in a few days.*

### Example: Bad
```
As a user, I want a complete social profile system
so that I can express my identity and connect with others.

Includes: Photo upload, bio, social links, privacy settings,
activity history, badges, followers, following, blocking...

Estimate: 3 sprints
```
*This is an epic, not a story.*

### How to Split Large Stories
1. **Workflow steps**: Split by user journey stages
2. **Operations**: Create, Read, Update, Delete as separate stories
3. **Data variations**: Handle different data types separately
4. **User roles**: Split by persona
5. **Platforms**: Split by device/platform
6. **Happy path first**: Core flow, then edge cases

### Splitting Patterns

| Pattern | Example |
|---------|---------|
| By workflow step | "Add to cart" vs "Checkout" vs "Payment" |
| By operation | "View orders" vs "Cancel order" vs "Reorder" |
| By data type | "Upload image" vs "Upload video" vs "Upload PDF" |
| By user role | "Customer views order" vs "Admin views order" |
| By complexity | "Basic search" vs "Advanced filters" |

---

## T - Testable

### Definition
Stories must have clear acceptance criteria that can be verified. If you cannot describe how to test it, it's not ready for development.

### Validation Checklist
- [ ] Acceptance criteria are specific and measurable
- [ ] Pass/fail determination is objective
- [ ] Test scenarios can be written from the story
- [ ] Edge cases are identified
- [ ] Non-functional criteria have thresholds

### Example: Good
```
As a user, I want to receive email notifications for new messages
so that I don't miss important communications.

Acceptance Criteria:
- Email is sent within 5 minutes of new message
- Email contains sender name and message preview (first 100 chars)
- Email has a "View Message" link that opens the conversation
- User can disable notifications in settings
- No email is sent if user is currently active in the app

Test Cases:
1. Send message, verify email received with correct content
2. Disable notifications, send message, verify no email
3. User active in app, send message, verify no email
```
*Specific, measurable, testable criteria.*

### Example: Bad
```
As a user, I want a better notification experience
so that I stay informed.

Acceptance Criteria:
- Notifications are improved
- User is happy with notifications
```
*Subjective. "Better" and "happy" are not testable.*

### How to Make Stories Testable
1. **Define specific outcomes**: What exactly should happen?
2. **Add numbers**: Response time < 2s, not "fast"
3. **Describe behavior**: "Button turns green" not "Button indicates success"
4. **Consider edge cases**: What about empty states, errors, limits?
5. **Write scenarios**: Given-When-Then format helps

---

## INVEST Validation Summary

### Quick Validation Matrix

| Criterion | Pass | Fail | Action if Fail |
|-----------|------|------|----------------|
| Independent | [ ] | [ ] | Split or combine stories |
| Negotiable | [ ] | [ ] | Remove implementation details |
| Valuable | [ ] | [ ] | Add "so that" clause, link to goals |
| Estimable | [ ] | [ ] | Spike, break down, or get expertise |
| Small | [ ] | [ ] | Split using patterns above |
| Testable | [ ] | [ ] | Add specific acceptance criteria |

### Story Health Score

- **6/6 criteria met**: Ready for development
- **4-5 criteria met**: Needs minor refinement
- **2-3 criteria met**: Needs significant work
- **0-1 criteria met**: Not a valid story, start over

---

## Common Anti-Patterns

### Anti-Pattern: Technical Story
```
As a developer, I want to upgrade to React 18...
```
**Fix**: Frame as user value or make it a tech task, not a story.

### Anti-Pattern: Epic in Disguise
```
As a user, I want a complete dashboard...
```
**Fix**: Split into individual dashboard widgets/features.

### Anti-Pattern: Compound Story
```
As a user, I want to create, edit, and delete posts...
```
**Fix**: Split into separate CRUD stories.

### Anti-Pattern: Solution-Focused
```
As a user, I want a Redis cache...
```
**Fix**: Describe the user need (faster loading), not the solution.

### Anti-Pattern: Vague Acceptance
```
Acceptance Criteria: Works correctly
```
**Fix**: Define specific, measurable criteria.
