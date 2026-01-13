# Agent Context Management v2.0

> **SIMPLIFIED PROTOCOL** - Uses Claude Code's built-in features

## Core Principle

**Claude Code has built-in context management. USE IT, don't replace it.**

Built-in features that work automatically:

- **Context editing**: Stale tool calls removed (29-39% improvement)
- **Auto-summarization**: Transparent token management
- **Subagent isolation**: Each agent has own context window

---

## Minimal Agent Prompts (MANDATORY)

### The Only Content Allowed in Agent Prompts

```
Task: [200 chars max]
Files: [3-5 specific files]
Output: JSON {filesModified, summary, errors}
Rules: Grep-first, LSP for navigation, JSON output
```

**Total prompt size: <500 characters**

### Forbidden in Agent Prompts

- Full conversation history
- All CLAUDE.md rules
- Progress file contents
- Previous agent outputs
- Debug context from other tasks

---

## Structured JSON Output (MANDATORY)

Agents MUST return this structure:

```json
{
  "success": boolean,
  "filesModified": ["path/to/file.ts"],
  "testsWritten": ["path/to/test.ts"],
  "summary": "max 500 chars describing what was done",
  "errors": ["error message if any"],
  "nextSteps": ["max 3 items"]
}
```

**No prose narratives. JSON only.**

---

## Context Commands (Between Waves)

### After Each Wave of 2-3 Agents

```bash
/clear  # Reset context before next wave
```

### Monitor Context Usage

```bash
/context  # Check current usage percentage
```

### Compact at 70%

```bash
/compact  # Trigger when approaching 70%
```

**Note**: The official threshold is 70%, not 60%.

---

## JIT File Loading + LSP Navigation

### DO (Lean Context)

1. Grep/Glob to find relevant files
2. Use LSP tools for smart navigation:
   - Go to definition
   - Find references
   - Get type information
3. Read ONLY files you're actively modifying
4. Make changes
5. Return structured summary
6. Files can be re-read later if needed

### LSP Tools Available

Claude Code has Language Server Protocol integration:

- **Definition**: Jump to where a function/type is defined
- **References**: Find all usages of a symbol
- **Type Info**: Get type information without reading full files

More efficient than reading entire files for context.

### DON'T (Context Bloat)

- Read 20 files "for context"
- Keep file contents in memory
- Load entire directories upfront
- Ignore LSP when it would help

---

## Agent Self-Management

Since agents have isolated context windows:

### When You See "Context low"

```bash
/compact Keep: current file, current test, current error
```

### Proactive Compaction at 60%

```bash
/compact Keep: implementation progress, files modified, test status
```

### Focus Your Compaction

Always specify what to preserve:

```
/compact
Preserve:
- Current file changes
- Test failures and causes
- Implementation decisions

Summarize:
- Exploration
- Failed attempts
- Old errors
```

---

## Token Budget Reference

| Component     | Old (Wrong)  | New (Correct) |
| ------------- | ------------ | ------------- |
| Agent prompt  | ~40K tokens  | <500 tokens   |
| File reads    | 50K+ tokens  | ~1K tokens    |
| Agent output  | ~20K tokens  | ~500 tokens   |
| **Per agent** | ~110K tokens | ~2K tokens    |
| **Wave of 3** | ~330K tokens | ~6K tokens    |

**98% reduction = 0 context overflows**

---

## Orchestrator Responsibilities

The orchestrator (not agents) handles:

1. **Wave management**: Clear context between waves
2. **Progress tracking**: Via memory-keeper MCP
3. **Verification**: Run typecheck/tests after agent returns
4. **Aggregation**: Combine agent JSON outputs

Agents focus on their single task only.

---

## Migration from v1

This replaces the complex monitoring systems in v1:

| v1 (Deprecated)         | v2 (Current)             |
| ----------------------- | ------------------------ |
| Python monitoring hooks | Built-in context editing |
| Manual token budgets    | JIT file loading         |
| Custom compaction logic | /compact at 70%          |
| Prose agent outputs     | Structured JSON          |

---

## Quick Reference Card

```
SPAWNING AGENTS:
  - Prompt < 500 chars
  - Include: task, files, output format
  - Exclude: history, rules, progress

AGENT BEHAVIOR:
  - Grep/Glob first to find files
  - Use LSP for definitions/references
  - Read only files you're modifying
  - Return JSON only

BETWEEN WAVES:
  - Run /clear
  - Check /context
  - Compact at 70%

AGENT SELF-CARE:
  - Watch for "Context low"
  - Proactive /compact at 60%
  - Focus on current task only
```

---

**Version**: 2.0
**Status**: ACTIVE
**Replaces**: agent-context.md (v1)
