# Minimal Agent Prompt Template

> Reference template for spawning agents with minimal context

## Template Structure

```
Task: [200 chars max - specific task description]
Files: [3-5 specific files to modify]
Output: JSON {filesModified, summary, errors}
Rules: Grep-first, LSP for navigation, JSON output
```

**Total: <500 characters**

---

## Examples

### Developer Agent

```
Task: Implement useQuizTimer hook with countdown logic and pause/resume
Files: src/hooks/useQuizTimer.ts, src/types/quiz.ts
Output: JSON {filesModified, testsWritten, summary, errors}
Rules: Grep-first, LSP for navigation, JSON output
```

### Test Agent

```
Task: Write tests for QuizResults component covering pass/fail states
Files: src/components/quiz/QuizResults.tsx, src/components/quiz/__tests__/
Output: JSON {testsWritten, coverage, summary, errors}
Rules: Read setup.ts first, follow existing patterns, JSON output
```

### Fix Agent

```
Task: Fix TypeScript error in useQuiz.ts line 45 - undefined check needed
Files: src/hooks/useQuiz.ts
Output: JSON {filesModified, errorFixed, summary}
Rules: Read error context, minimal change, JSON output
```

### Refactor Agent

```
Task: Extract common quiz state logic into shared hook
Files: src/hooks/useQuiz.ts, src/hooks/useQuizTimer.ts, src/hooks/shared/
Output: JSON {filesModified, filesCreated, summary, errors}
Rules: Grep existing patterns, LSP for refs, JSON output
```

---

## Required JSON Output Schema

All agents MUST return this structure:

```json
{
  "success": true,
  "filesModified": ["src/hooks/useQuiz.ts"],
  "testsWritten": ["src/hooks/__tests__/useQuiz.test.ts"],
  "summary": "Implemented quiz state management with timer support. Added pause/resume functionality and countdown display.",
  "errors": [],
  "nextSteps": ["Add edge case tests", "Integrate with QuizContainer"]
}
```

### Field Constraints

| Field         | Type     | Constraint        |
| ------------- | -------- | ----------------- |
| success       | boolean  | Required          |
| filesModified | string[] | Required          |
| testsWritten  | string[] | Optional          |
| summary       | string   | **Max 500 chars** |
| errors        | string[] | Optional          |
| nextSteps     | string[] | Max 3 items       |

---

## Navigation Strategy

### Use LSP Tools

```
1. Find definitions: Use LSP to jump to type/function definitions
2. Find references: Use LSP to see where things are used
3. Get type info: Use LSP to understand types without reading files
```

### Grep/Glob First

```
1. Grep for patterns: Find relevant code locations
2. Glob for files: Find files matching patterns
3. Then read: Only read files you're actually modifying
```

---

## What NOT to Include

Never add these to agent prompts:

- Conversation history from orchestrator
- Full CLAUDE.md rules
- PROGRESS.md contents
- Previous agent outputs
- Debug logs from other tasks
- "Context" files not being modified

---

## Context Management Reminders

Include in agent prompts if needed:

```
Context Notes:
- Run /compact if you see "Context low"
- Use LSP for type info instead of reading files
- Return JSON summary, not prose
```

---

## Quick Copy Templates

### Implementation Task

```
Task: [TASK]
Files: [FILES]
Output: JSON {filesModified, testsWritten, summary, errors}
Rules: Grep-first, LSP for navigation, JSON output
```

### Test Task

```
Task: [TASK]
Files: [FILES]
Output: JSON {testsWritten, coverage, summary, errors}
Rules: Read setup.ts first, follow patterns, JSON output
```

### Fix Task

```
Task: [TASK]
Files: [FILES]
Output: JSON {filesModified, errorFixed, summary}
Rules: Minimal change, verify fix, JSON output
```

---

**Version**: 1.0
**Last Updated**: 2026-01-04
