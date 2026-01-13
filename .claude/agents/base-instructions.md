# Agent Base Instructions

> **INJECT INTO EVERY AGENT PROMPT - MANDATORY**

## Context Management (MANDATORY - NOT OPTIONAL)

```
╔═══════════════════════════════════════════════════════════════════╗
║  YOU MUST MANAGE YOUR OWN CONTEXT OR YOU WILL FAIL                ║
║                                                                   ║
║  "Context low" → STOP. RUN /compact. CONTINUE.                   ║
║  60% usage     → RUN /compact PROACTIVELY                        ║
║  10+ files     → RUN /compact BEFORE CONTINUING                  ║
║                                                                   ║
║  NO EXCEPTIONS. NO ASKING FOR HELP. JUST DO IT.                  ║
╚═══════════════════════════════════════════════════════════════════╝
```

### REQUIRED Actions

1. **At 60% usage OR after processing 10+ files**: **MUST** run `/compact`
2. **If you see "Context low"**: **STOP EVERYTHING**, run `/compact`, then continue
3. **If responses feel slow**: Run `/compact` - don't wait

### Compact Command Template

```
/compact
KEEP: [current file], [current test], [implementation progress], [remaining tasks]
SUMMARIZE: research, exploration, old errors, debugging attempts
```

### JIT Loading Pattern

- **DON'T** read entire directories upfront
- **DO** read specific files when modifying them
- **DON'T** keep file contents after processing
- **DO** re-read if needed later (files persist on disk)

---

## Task Completion Protocol

### 1. Understand Task

- Read task requirements
- Identify specific files to modify
- Plan approach (don't over-plan)

### 2. Execute with Lean Context

**Navigation Strategy**:

- **Use Grep/Glob** to find relevant files
- **Use LSP tools** for smart navigation:
  - Go to definition
  - Find references
  - Get type information (without reading full files)
- **Read ONLY** files you're actively modifying
- Make changes
- Run targeted tests
- Move to next file

### 3. Quality Gates

Before reporting completion:

```bash
pnpm typecheck  # Must pass (0 errors)
pnpm lint       # Must pass
pnpm test       # Relevant tests pass
```

---

## TypeScript Type Safety (MANDATORY)

```
╔═══════════════════════════════════════════════════════════════════╗
║  BEFORE WRITING ANY TYPESCRIPT CODE:                              ║
║                                                                   ║
║  1. Check @/types/registry for existing types                    ║
║  2. Import ALL types from @/types/registry                       ║
║  3. Run `pnpm typecheck` before returning results                ║
║                                                                   ║
║  NO 'any' TYPES, EVER. NO EXCEPTIONS.                            ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Pre-Code Checklist

**Before creating ANY new type**:

```bash
# 1. Search registry
grep "TypeName" src/types/registry.ts

# 2. Search existing types
grep -r "interface TypeName\|type TypeName" src/types/

# 3. If exists → use it. If not → add to registry
```

### Type Import Pattern

```typescript
// ❌ WRONG - Never import from individual files
import { User } from "@/types/index";
import { QuizAttempt } from "@/types/quiz";

// ✅ CORRECT - Always import from registry
import { User, QuizAttempt, AsyncState, Result } from "@/types/registry";
```

### Validation Loop (MANDATORY)

```
1. Write code
2. Run: pnpm typecheck
3. IF errors → Read errors → Fix → Go to step 2
4. Run: pnpm lint
5. IF errors → Fix → Go to step 2
6. ONLY THEN return code
```

### 4. Return Structured JSON Output

**MANDATORY**: Report back to orchestrator using this JSON schema:

```json
{
  "success": true,
  "filesModified": ["src/hooks/useQuiz.ts"],
  "testsWritten": ["src/hooks/__tests__/useQuiz.test.ts"],
  "summary": "Implemented quiz state management with timer support (max 500 chars)",
  "errors": [],
  "nextSteps": ["Add edge case tests", "Integrate with container"]
}
```

**Field Requirements**:

- `success` (boolean): Required - true if task completed
- `filesModified` (string[]): Required - all files changed
- `testsWritten` (string[]): Optional - test files created/modified
- `summary` (string): Required - **max 500 chars** describing what was done
- `errors` (string[]): Optional - any errors encountered
- `nextSteps` (string[]): Optional - **max 3 items** for follow-up work

**Important**: Return ONLY the JSON object, no markdown formatting or prose.

---

## Orchestrator Expectations

The orchestrator:

- Gave you a specific, scoped task
- Expects you to complete it autonomously
- Will NOT help with context management
- Needs a clear summary when you're done

You are responsible for:

- Managing your own context
- Completing the assigned task
- Running quality checks
- Reporting results clearly

---

## Recovery After Compaction

After `/compact`, you may lose some details. This is fine:

1. Re-read the specific file you're working on
2. Re-run the failing test
3. Continue from where you left off

The work you've written to disk is safe. Only conversation history is compacted.

---

## Common Pitfalls

### DON'T

- Read everything upfront "to understand the codebase"
- Keep exploring without compacting
- Wait until "Context low" to compact
- Ask orchestrator for help with context

### DO

- Start working immediately on the task
- Compact at 60% proactively
- Re-read files as needed (they're still there)
- Complete task and return summary
