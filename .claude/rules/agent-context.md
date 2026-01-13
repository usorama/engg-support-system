# Agent Context Management Rules

> **MANDATORY COMPLIANCE REQUIRED** - These are NOT suggestions. Failure = task failure.

## NON-NEGOTIABLE REQUIREMENTS

```
┌─────────────────────────────────────────────────────────────────┐
│  EVERY AGENT MUST:                                              │
│  1. RUN /compact IMMEDIATELY when seeing "Context low"          │
│  2. RUN /compact PROACTIVELY at 60% or after 10 files          │
│  3. USE JIT LOADING - read files only when modifying            │
│  4. NEVER STALL - if context low, compact and continue          │
│                                                                 │
│  FAILURE TO COMPACT = TASK FAILURE = WORKFLOW BLOCKED           │
└─────────────────────────────────────────────────────────────────┘
```

## Why This Is MANDATORY

Agents spawned via Task tool have isolated context windows. Without self-management:

- You WILL hit "Context low" and stall
- Your work WILL be lost
- Orchestrator CANNOT help you - you're on your own
- The ENTIRE workflow blocks waiting for YOU

## REQUIRED Self-Monitoring Protocol

### 1. MUST Watch for Context Signals

When you see ANY of these, **STOP EVERYTHING AND RUN `/compact`**:

- "Context low" message → **IMMEDIATE /compact, NO EXCEPTIONS**
- Sluggish responses → Run `/compact` now
- Repeated information requests → Run `/compact` now
- You've processed 10+ files → Run `/compact` now

### 2. MUST Compact Proactively

**DO NOT wait for warnings.** At approximately **60% usage**:

```
/compact Keep: current implementation progress, test status, files being modified.
Summarize: research, debugging attempts, file exploration, old errors.
```

### 3. Focus Your Compaction

Always specify what to preserve:

```
/compact
Preserve:
- Current file changes (list specific files)
- Test failures and their causes
- Implementation decisions made
- Open issues to address

Summarize:
- Exploration of codebase
- Failed debugging attempts
- Old error messages
- Research that's already applied
```

## JIT Context Loading Pattern

### DON'T (Context Bloat)

```
# Bad: Read everything upfront
Read entire src/ directory
Read all test files
Read all documentation
Then start working...
```

### DO (Lean Context)

```
# Good: Read only what you need, when you need it
1. Understand task requirements
2. Read ONLY the file you're about to modify
3. Make changes
4. Read test file for that specific component
5. Run tests
6. Move on (file contents can be re-read if needed)
```

## After Processing - Discard

After you've processed a file:

- You've extracted what you need
- The file still exists on disk
- If you need it again, you can re-read it
- DON'T keep full file contents in your "memory"

## Compaction Commands

### Quick Compact (60% usage)

```
/compact Keep implementation progress and current task state
```

### Deep Compact (70%+ usage)

```
/compact
KEEP:
- All code changes made this session
- Current test status
- Files still to modify
- Critical decisions

SUMMARIZE:
- Everything else
```

### Emergency Compact (80%+ / "Context low")

```
/compact Keep only: current file, current test, current error to fix
```

## Recovery After Compaction

After compacting, you may need to re-gather context:

1. Re-read the specific file you're working on
2. Re-run the specific test that's failing
3. Continue from where you left off

This is normal and expected - it's better than losing all progress!

## Integration with Orchestrator

The orchestrator:

- Spawns you with a specific task
- Expects you to handle your own context
- Will receive your results summary
- Does NOT retain your detailed work

You are responsible for:

- Completing your assigned task
- Managing your own context
- Returning a clear summary of what you did

## Example Agent Session

```
1. Receive task: "Implement UserService with tests"
2. Read only UserService.ts (if exists)
3. Implement changes
4. Read only UserService.test.ts
5. Write tests
6. Run tests
7. If at 60%: /compact Keep: implementation, test status
8. Fix any failures
9. Return summary to orchestrator
```

## Remember

- Your context is YOUR responsibility
- Compact early, compact often
- JIT loading > upfront loading
- Files are re-readable, don't hoard them
- Focus compaction on what you're actively working on
