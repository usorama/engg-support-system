# Tasks.json Schema Documentation

## Overview

The `tasks.json` file is the machine-readable task tracking system for project management. It enables automated progress tracking, dependency resolution, and verification of completed work.

---

## Full Schema Definition

```json
{
  "id": "string",
  "type": "setup|code|test|doc|design|research|refactor|deploy|config",
  "priority": "P0|P1|P2|P3",
  "phase": "number (0-5)",
  "description": "string",
  "dependencies": ["string[]"],
  "context_files": ["string[]"],
  "instruction": "string",
  "verification": {
    "type": "test_pass|file_exists|command_success|manual|lint_pass|build_success",
    "command": "string (optional)",
    "files": ["string[] (optional)"],
    "criteria": "string (optional)"
  },
  "status": "pending|in_progress|completed|blocked|cancelled",
  "blocked_by": "string (optional - reason or task ID)",
  "assignee": "string (optional)",
  "estimate_hours": "number (optional)",
  "actual_hours": "number (optional)",
  "started_at": "ISO datetime (optional)",
  "completed_at": "ISO datetime (optional)",
  "notes": "string (optional)",
  "tags": ["string[] (optional)"]
}
```

---

## Field Descriptions

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier following pattern `TASK-XXX` or `{PREFIX}-XXX` |
| `type` | enum | Category of work (see valid values below) |
| `priority` | enum | Priority level P0 (critical) through P3 (nice-to-have) |
| `phase` | number | Development phase 0-5 |
| `description` | string | Brief human-readable description of the task |
| `status` | enum | Current state of the task |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `dependencies` | string[] | Array of task IDs that must complete before this task |
| `context_files` | string[] | Files relevant to this task (for AI context loading) |
| `instruction` | string | Detailed implementation instructions |
| `verification` | object | How to verify task completion |
| `blocked_by` | string | Reason or task ID causing blockage |
| `assignee` | string | Who is responsible for this task |
| `estimate_hours` | number | Estimated hours to complete |
| `actual_hours` | number | Actual hours spent |
| `started_at` | string | ISO 8601 datetime when work began |
| `completed_at` | string | ISO 8601 datetime when task was marked complete |
| `notes` | string | Additional context or comments |
| `tags` | string[] | Labels for filtering and categorization |

---

## Valid Values

### Type Values

| Value | Description | Examples |
|-------|-------------|----------|
| `setup` | Environment, tooling, configuration | Install dependencies, configure CI/CD |
| `code` | Feature implementation | Add login form, implement API endpoint |
| `test` | Test creation or updates | Unit tests, integration tests, E2E tests |
| `doc` | Documentation | README, API docs, architecture docs |
| `design` | UI/UX design work | Wireframes, mockups, design system |
| `research` | Investigation, spike, POC | Evaluate libraries, research approaches |
| `refactor` | Code improvement without feature change | Extract component, improve performance |
| `deploy` | Deployment and release | Deploy to staging, production release |
| `config` | Configuration changes | Update env vars, modify settings |

### Priority Values

| Value | Meaning | SLA |
|-------|---------|-----|
| `P0` | Critical blocker | Must complete immediately |
| `P1` | High priority, required for milestone | Complete this sprint |
| `P2` | Medium priority, important but not urgent | Complete within 2 sprints |
| `P3` | Low priority, nice-to-have | Backlog |

### Phase Values

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Foundation | Project setup, tooling, infrastructure |
| 1 | Core | Core features, MVP functionality |
| 2 | Enhancement | Feature improvements, UX polish |
| 3 | Integration | Third-party integrations, data sync |
| 4 | Testing | Comprehensive testing, QA |
| 5 | Release | Documentation, deployment, launch |

### Status Values

| Value | Description | Can Transition To |
|-------|-------------|-------------------|
| `pending` | Not started | `in_progress`, `blocked`, `cancelled` |
| `in_progress` | Currently being worked on | `completed`, `blocked`, `pending` |
| `completed` | Done and verified | (terminal state) |
| `blocked` | Cannot proceed | `pending`, `in_progress`, `cancelled` |
| `cancelled` | No longer needed | (terminal state) |

---

## Verification Patterns

### Test Pass
```json
{
  "verification": {
    "type": "test_pass",
    "command": "pnpm test src/components/Button.test.tsx"
  }
}
```

### File Exists
```json
{
  "verification": {
    "type": "file_exists",
    "files": [
      "src/components/Button.tsx",
      "src/components/Button.test.tsx"
    ]
  }
}
```

### Command Success
```json
{
  "verification": {
    "type": "command_success",
    "command": "pnpm run typecheck && pnpm run lint"
  }
}
```

### Build Success
```json
{
  "verification": {
    "type": "build_success",
    "command": "pnpm run build"
  }
}
```

### Lint Pass
```json
{
  "verification": {
    "type": "lint_pass",
    "command": "pnpm run lint --max-warnings 0"
  }
}
```

### Manual Verification
```json
{
  "verification": {
    "type": "manual",
    "criteria": "Verify login flow works with test credentials in staging environment"
  }
}
```

---

## Example Tasks

### Setup Task
```json
{
  "id": "TASK-001",
  "type": "setup",
  "priority": "P0",
  "phase": 0,
  "description": "Initialize project with Vite + React + TypeScript",
  "dependencies": [],
  "context_files": ["package.json", "vite.config.ts", "tsconfig.json"],
  "instruction": "Run create-vite with react-ts template. Configure path aliases. Add ESLint and Prettier.",
  "verification": {
    "type": "command_success",
    "command": "pnpm run dev --port 3000 & sleep 5 && curl -s http://localhost:3000 | grep -q 'Vite'"
  },
  "status": "pending",
  "estimate_hours": 2,
  "tags": ["foundation", "tooling"]
}
```

### Code Task
```json
{
  "id": "TASK-010",
  "type": "code",
  "priority": "P1",
  "phase": 1,
  "description": "Implement user authentication with Firebase",
  "dependencies": ["TASK-001", "TASK-005"],
  "context_files": [
    "src/lib/firebase.ts",
    "src/hooks/useAuth.ts",
    "src/context/AuthContext.tsx"
  ],
  "instruction": "Create AuthContext with Firebase Auth. Implement sign-in, sign-out, and sign-up methods. Add loading and error states. Persist auth state.",
  "verification": {
    "type": "test_pass",
    "command": "pnpm test src/hooks/useAuth.test.ts"
  },
  "status": "pending",
  "estimate_hours": 8,
  "tags": ["auth", "firebase", "mvp"]
}
```

### Test Task
```json
{
  "id": "TASK-015",
  "type": "test",
  "priority": "P1",
  "phase": 1,
  "description": "Add unit tests for authentication hooks",
  "dependencies": ["TASK-010"],
  "context_files": [
    "src/hooks/useAuth.ts",
    "src/hooks/useAuth.test.ts"
  ],
  "instruction": "Write unit tests for useAuth hook. Test sign-in, sign-out, error handling, loading states. Mock Firebase Auth. Achieve 90% coverage.",
  "verification": {
    "type": "command_success",
    "command": "pnpm test --coverage src/hooks/useAuth.test.ts && grep -q '90' coverage/lcov-report/index.html"
  },
  "status": "pending",
  "estimate_hours": 4,
  "tags": ["testing", "auth"]
}
```

### Documentation Task
```json
{
  "id": "TASK-050",
  "type": "doc",
  "priority": "P2",
  "phase": 5,
  "description": "Create API documentation for authentication endpoints",
  "dependencies": ["TASK-010", "TASK-011"],
  "context_files": ["docs/api/auth.md"],
  "instruction": "Document all auth-related API endpoints. Include request/response schemas, error codes, examples. Use OpenAPI format.",
  "verification": {
    "type": "file_exists",
    "files": ["docs/api/auth.md", "docs/api/openapi.yaml"]
  },
  "status": "pending",
  "estimate_hours": 3,
  "tags": ["documentation", "api"]
}
```

---

## Status Transition Rules

```
                    ┌─────────────┐
                    │   pending   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐  ┌───────────┐  ┌───────────┐
       │ blocked  │  │in_progress│  │ cancelled │
       └────┬─────┘  └─────┬─────┘  └───────────┘
            │              │
            └──────┬───────┘
                   ▼
            ┌───────────┐
            │ completed │
            └───────────┘
```

### Transition Actions

| From | To | Trigger |
|------|----|---------|
| pending | in_progress | Work begins, set `started_at` |
| pending | blocked | Dependency fails or external blocker |
| pending | cancelled | Task no longer needed |
| in_progress | completed | Verification passes, set `completed_at` |
| in_progress | blocked | Encountered blocker during work |
| in_progress | pending | Deprioritized, work paused |
| blocked | pending | Blocker resolved |
| blocked | in_progress | Blocker resolved, resume work |
| blocked | cancelled | Cannot resolve, task abandoned |

---

## Best Practices

1. **Task IDs**: Use consistent prefix (PROJECT-XXX or TASK-XXX)
2. **Dependencies**: Keep dependency chains shallow (max 3 levels)
3. **Context Files**: Include all files the AI needs to understand the task
4. **Instructions**: Be specific - include file paths, function names, patterns
5. **Verification**: Always include verification - no task is complete without proof
6. **Estimates**: Use Fibonacci (1, 2, 3, 5, 8, 13) hours
7. **Tags**: Use consistent tag taxonomy across project

---

## File Structure

```
project/
├── tasks.json           # Main task file
├── PROGRESS.md          # Human-readable progress
└── .claude/
    └── tasks/
        ├── archive/     # Completed sprints
        │   ├── sprint-1.json
        │   └── sprint-2.json
        └── templates/   # Task templates
```
