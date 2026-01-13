---
name: progress-tracker
description: Track and report project progress automatically. Use for checking status, updating progress, sprint review, current state.
allowed-tools: Read, Write, Glob, Grep
---

# Progress Tracker Skill

Track and manage project progress across sessions.

## Progress File Locations

- `.ai/PROGRESS.md` - Current session progress
- `docs/tasks/kanban_board.md` - Task board
- `docs/tasks/backlog.md` - Future items
- `docs/planning/tasks.json` - Machine-readable tasks

## Progress File Structure

```markdown
# Progress Tracker

## Current Status

- **Phase**: [Discovery/Specification/Architecture/Implementation/...]
- **Current Epic**: [Epic ID and name]
- **Current Story**: [Story ID and name]
- **Blockers**: [Any blockers or None]

## Session Context

- Last updated: [ISO timestamp]
- Session ID: [Optional identifier]

## Recently Completed

- [x] Task/Story 1
- [x] Task/Story 2

## In Progress

- [ ] Current task (XX%)

## Next Steps

1. Immediate next action
2. Following action

## Key Decisions

- Decision: [What] because [Why]

## Open Questions

- [ ] Question needing resolution
```

## Update Protocol

### After Completing a Task

1. Mark task complete in kanban_board.md
2. Update .ai/PROGRESS.md
3. Update tasks.json status
4. Move to next task

### Session Start

1. Read .ai/PROGRESS.md
2. Read tasks.json for pending tasks
3. Report current status
4. Suggest next actions

### Session End

1. Update .ai/PROGRESS.md with current state
2. Document any blockers
3. Note next steps for continuity

## Status Report Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PROJECT STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase: [Current Phase]
Sprint: [Sprint Number] (Day X/Y)

Progress:
├── Completed: X stories
├── In Progress: Y stories
└── Remaining: Z stories

Current: [Story ID] - [Title]
Blockers: [None / List]

Next Actions:
1. [Action 1]
2. [Action 2]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
