---
name: plan
description: Generate execution plans from user queries through intake, research, specification, and validation. Use when user provides any query (vague to specific) and needs an executable plan for /execute skill.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion
model: claude-sonnet-4-20250514
---

# /plan Skill - Hybrid Planning System

> **Version**: 1.0.0
> **Status**: Active
> **Purpose**: Generate evidence-backed execution plans consumable by /execute skill

---

## Core Principles

1. **User-Centric**: Accept queries from vague to specific
2. **Evidence-Based**: All technical decisions traced to verified sources
3. **Parallel Research**: 2-3 concurrent agents (max 2-3 concurrent enforced by ResourceManager)
4. **Structured Output**: YAML metadata + tasks.json for /execute skill
5. **Fast Intake**: 5-10 questions max, <5 minutes for simple queries

---

## Phase 0: Startup Protocol

### Required Context Loads

```bash
# Read skill configuration
cat .claude/skills/plan/SKILL.md

# Read rad-engineer components (understand execution capabilities)
cat rad-engineer/SYSTEM_ARCHITECTURE_COMPREHENSIVE.md
cat rad-engineer/README.md

# Check for existing project structure
if [ -f docs/planning/execution/GRANULAR_EXECUTION_PLAN.md ]; then
  echo "Existing plan found - will update or create new version"
fi

# Initialize ResourceManager (enforces 2-3 agent limit)
# This is critical for parallel research phase
```

### Initial State

```
┌─────────────────────────────────────────────────────────────┐
│                    STARTUP STATE                           │
├─────────────────────────────────────────────────────────────┤
│  Input: User Query (vague to specific)                      │
│  Context: rad-engineer components available                 │
│  Constraint: Max 2-3 concurrent agents                      │
│  Output: GRANULAR_EXECUTION_PLAN.md + tasks.json            │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Intake (User Query → Structured Requirements)

### Step 1.1: Receive User Query

User provides query in natural language:

```
Examples:
- "build me notion like notes app"
- "add authentication to my API"
- "implement search functionality"
```

### Step 1.2: Ask Clarifying Questions (5-10 max)

Use `AskUserQuestion` tool to gather required information:

```javascript
AskUserQuestion({
  questions: [
    {
      question: "What is the main feature you want to build?",
      header: "Core Feature",
      multiSelect: false,
      options: [
        { label: "New feature from scratch", description: "Building something completely new" },
        { label: "Enhancement to existing", description: "Adding to/modifying existing code" },
        { label: "Bug fix", description: "Fixing a specific issue" }
      ]
    },
    {
      question: "What technical stack should we use?",
      header: "Tech Stack",
      multiSelect: false,
      options: [
        { label: "TypeScript/Node.js", description: "Recommended for rad-engineer projects" },
        { label: "Python/FastAPI", description: "For Python-based services" },
        { label: "Other (specify)", description: "Will use custom tech stack" }
      ]
    },
    {
      question: "What's the timeline for this feature?",
      header: "Timeline",
      multiSelect: false,
      options: [
        { label: "ASAP", description: "Urgent, prioritize speed" },
        { label: "This week", description: "Standard sprint timeline" },
        { label: "Flexible", description: "No specific deadline" }
      ]
    },
    {
      question: "What are the success criteria?",
      header: "Success Criteria",
      multiSelect: true,
      options: [
        { label: "Tests passing", description: "All tests must pass (≥80% coverage)" },
        { label: "TypeScript strict", description: "Zero typecheck errors" },
        { label: "Documentation", description: "Include inline documentation" },
        { label: "Working demo", description: "Runnable demonstration" }
      ]
    },
    {
      question: "What should we NOT include (scope boundaries)?",
      header: "Out of Scope",
      multiSelect: true,
      options: [
        { label: "Database schema changes", description: "No DB modifications" },
        { label: "API changes", description: "No breaking API changes" },
        { label: "UI/UX design", description: "Focus on backend only" },
        { label: "Performance optimization", description: "Functional requirements only" }
      ]
    }
  ]
})
```

### Step 1.3: Build StructuredRequirements

From user answers, construct:

```typescript
interface StructuredRequirements {
  query: string                    // Original user query
  coreFeature: string              // Main feature to build
  techStack: string                // Technology stack
  timeline: string                 // Timeline constraint
  successCriteria: string[]        // Success criteria
  outOfScope: string[]             // Explicitly excluded items
  complexity: 'simple' | 'medium' | 'complex'
  estimatedStories: number         // Rough story count
}
```

---

## Phase 2: Research (Parallel Agents)

### Step 2.1: Calculate Agent Count

```typescript
// ResourceManager enforces max 2-3 concurrent
const agentCount = Math.min(
  requirements.complexity === 'complex' ? 3 : 2,
  3  // Hard limit from ResourceManager
);
```

### Step 2.2: Spawn Research Agents

**CRITICAL**: Use `run_in_background: true` for parallel execution

```markdown
# Spawn 2-3 research agents in PARALLEL

Agent 1: Technical Feasibility
──────────────────────────────────
Task: "Research technical approaches for: [coreFeature]

Requirements to investigate:
- Tech stack: [techStack]
- Timeline: [timeline]
- Success criteria: [successCriteria]

Research focus:
1. Technical feasibility (can this be built?)
2. Recommended approaches (2-3 options with pros/cons)
3. Potential blockers or risks
4. Estimated complexity (simple/medium/complex)

Output: JSON
{
  'feasible': boolean,
  'approaches': [{'name': string, 'pros': string[], 'cons': string[], 'confidence': number}],
  'risks': [{'risk': string, 'mitigation': string}],
  'complexity': 'simple' | 'medium' | 'complex',
  'evidence': [{'claim': string, 'source': string, 'confidence': number}]
}

Rules: Grep-first, LSP for navigation, JSON output"

Agent 2: Codebase Patterns (if enhancement)
────────────────────────────────────────────
Task: "Analyze existing codebase patterns for: [coreFeature]

Glob/Grep to find:
1. Similar existing features (pattern matching)
2. Codebase conventions (file structure, naming)
3. Integration points (where to connect)
4. Dependencies (what already exists)

Output: JSON
{
  'similarFeatures': [{'file': string, 'pattern': string, 'reusable': boolean}],
  'conventions': {'structure': string, 'naming': string, 'testing': string},
  'integrationPoints': [{'location': string, 'type': string, 'requirements': string[]}],
  'existingDependencies': string[],
  'evidence': [{'claim': string, 'source': string, 'confidence': number}]
}

Rules: Grep-first, LSP for navigation, JSON output"

Agent 3: Best Practices (optional - for complex features)
──────────────────────────────────────────────────────────
Task: "Research best practices for: [coreFeature]

Context7 queries for:
1. Library documentation (if using specific libraries)
2. Framework best practices
3. Common pitfalls and anti-patterns
4. Security considerations

Output: JSON
{
  'bestPractices': [{'practice': string, 'reason': string, 'source': string}],
  'pitfalls': [{'pitfall': string, 'consequence': string, 'avoidance': string}],
  'securityConsiderations': [{'risk': string, 'mitigation': string}],
  'evidence': [{'claim': string, 'source': string, 'confidence': number}]
}

Rules: Use context7 for docs, web search for current patterns, JSON output"
```

### Step 2.3: Collect Research Results

```bash
# Wait for all research agents to complete
# Collect outputs via TaskOutput
```

### Step 2.4: Consolidate Findings

Create `RESEARCH_FINDINGS.md`:

```markdown
# Research Findings

## Feasibility
[From Agent 1]

## Technical Approaches
[From Agent 1 - ranked by confidence]

## Codebase Analysis
[From Agent 2 - existing patterns]

## Best Practices
[From Agent 3 - verified patterns]

## Risk Assessment
[Consolidated from all agents]

## Evidence Sources
[All sources with confidence scores]
```

---

## Phase 3: Specification

### Step 3.1: Generate Component Specifications

For each major component:

```typescript
interface ComponentSpec {
  componentId: string
  name: string
  purpose: string
  dependencies: string[]
  api: {
    inputs: Record<string, {type: string, required: boolean}>
    outputs: Record<string, {type: string}>
  }
  dataModels: Array<{
    name: string
    fields: Record<string, {type: string, nullable: boolean}>
  }>
  evidence: string[]  // Links to research findings
}
```

### Step 3.2: Create Integration Specifications

```typescript
interface IntegrationSpec {
  integrationId: string
  type: 'api' | 'database' | 'service' | 'ui'
  provider: string
  contract: {
    endpoint?: string
    method?: string
    protocol: string
  }
  requirements: string[]
  evidence: string[]
}
```

### Step 3.3: Output Specification Files

Create `docs/planning/specs/` directory:

```
docs/planning/specs/
├── component-specs.md
├── integration-specs.md
└── data-models.md
```

---

## Phase 4: Execution Plan Generation

### Step 4.1: Break Down into Stories

From research + specs, generate stories:

```typescript
interface Story {
  id: string                   // STORY-XXX-Y
  waveId: string               // wave-N.M
  title: string
  description: string
  acceptanceCriteria: string[]
  filesInScope: string[]
  testRequirements: {
    unitTests: number
    integrationTests: number
    coverageTarget: number
  }
  estimatedMinutes: number
  model: 'haiku' | 'sonnet' | 'opus'
  dependencies: string[]       // Story IDs
  parallelGroup: number        // Stories in same group can run parallel
}
```

### Step 4.2: Organize into Waves

```typescript
interface Wave {
  id: string                   // wave-N.M
  number: number               // N.M
  phase: 0 | 1 | 2 | 3        // 0=foundation, 1=features, 2=qa, 3=polish
  name: string
  dependencies: string[]       // Wave IDs
  estimatedMinutes: number
  parallelization: 'full' | 'partial' | 'sequential'
  maxConcurrent: number        // 2-3 enforced by ResourceManager
  stories: Story[]
}
```

### Step 4.3: Select Models per Story

Cost optimization strategy:

| Story Size | Model | Rationale |
|------------|-------|-----------|
| XS (<2hr) | haiku | Fast, cheap, sufficient |
| S (2-4hr) | haiku | Balanced |
| M (4-8hr) | sonnet | Higher quality |
| L (1-2d) | sonnet | Complex reasoning |
| XL (2-3d) | opus | Maximum quality |

### Step 4.4: Generate GRANULAR_EXECUTION_PLAN.md

**Location**: `docs/planning/execution/GRANULAR_EXECUTION_PLAN.md`

```yaml
# GRANULAR_EXECUTION_PLAN.md
execution_metadata:
  version: "1.0"
  schema: "rad-engineer-execution-metadata-v1"
  project: "[project-name]"
  created: "[YYYY-MM-DDTHH:mm:ssZ]"
  updated: "[YYYY-MM-DDTHH:mm:ssZ]"
  source: "/plan skill v1.0.0"
  research_session_id: "[UUID]"

requirements:
  query: "[original user query]"
  core_feature: "[from intake]"
  tech_stack: "[from intake]"
  timeline: "[from intake]"
  success_criteria: [from intake]
  out_of_scope: [from intake]

waves:
  - id: "wave-0.1"
    number: 0.1
    phase: 0
    name: "Foundation Setup"
    dependencies: []
    estimated_minutes: 60
    parallelization: "full"
    max_concurrent: 2
    stories:
      - id: "STORY-001-1"
        wave_id: "wave-0.1"
        title: "Initialize Project Structure"
        description: "Set up base project with TypeScript, tests, and linting"
        agent_type: "developer"
        model: "haiku"
        estimated_minutes: 30
        dependencies: []
        parallel_group: 1
        acceptance_criteria:
          - criterion: "package.json exists with dependencies"
          - criterion: "tsconfig.json configured"
          - criterion: "Test setup working"
        files_in_scope:
          - "package.json"
          - "tsconfig.json"
          - "test/setup.ts"
        test_requirements:
          unit_tests: 3
          integration_tests: 0
          coverage_target: 80

integration_tests:
  - wave_id: "wave-0.1"
    tests:
      - name: "Verify project structure"
        test_file: "test/setup.test.ts"

quality_gates:
  - wave_id: "all"
    gates:
      - name: "TypeScript compilation"
        command: "pnpm typecheck"
        must_pass: true
      - name: "Lint"
        command: "pnpm lint"
        must_pass: true
      - name: "Tests"
        command: "pnpm test"
        threshold: "80%"
        must_pass: true
```

### Step 4.5: Generate tasks.json

**Location**: `docs/planning/tasks.json`

```json
{
  "version": "1.0",
  "schema": "rad-engineer-tasks-v1",
  "project": "[project-name]",
  "generatedAt": "[YYYY-MM-DDTHH:mm:ssZ]",
  "stories": [
    {
      "id": "STORY-001-1",
      "waveId": "wave-0.1",
      "title": "Initialize Project Structure",
      "status": "pending",
      "model": "haiku",
      "estimatedMinutes": 30,
      "dependencies": [],
      "acceptanceCriteria": [
        "package.json exists with dependencies",
        "tsconfig.json configured",
        "Test setup working"
      ],
      "filesInScope": [
        "package.json",
        "tsconfig.json",
        "test/setup.ts"
      ],
      "testRequirements": {
        "unitTests": 3,
        "integrationTests": 0,
        "coverageTarget": 80
      }
    }
  ]
}
```

---

## Phase 5: Validation

### Step 5.1: Evidence Alignment Check

```typescript
// All claims must have evidence sources
function validateEvidenceAlignment(plan: ExecutionPlan): ValidationResult {
  const claims = extractAllClaims(plan);
  const evidence = plan.evidence || [];

  const unverifiedClaims = claims.filter(claim =>
    !evidence.some(ev => ev.claim === claim)
  );

  return {
    passed: unverifiedClaims.length === 0,
    issues: unverifiedClaims.map(claim => ({
      severity: 'error',
      message: `Claim "${claim}" has no evidence source`,
      location: 'research-findings'
    }))
  };
}
```

### Step 5.2: Completeness Check

```typescript
// All required fields must be present
function validateCompleteness(plan: ExecutionPlan): ValidationResult {
  const required = [
    'execution_metadata',
    'requirements',
    'waves',
    'quality_gates'
  ];

  const missing = required.filter(field => !plan[field]);

  return {
    passed: missing.length === 0,
    issues: missing.map(field => ({
      severity: 'error',
      message: `Missing required field: ${field}`,
      location: field
    }))
  };
}
```

### Step 5.3: Dependency Validation

```typescript
// No circular dependencies
function validateDependencies(plan: ExecutionPlan): ValidationResult {
  const graph = buildDependencyGraph(plan.waves);
  const cycles = detectCycles(graph);

  return {
    passed: cycles.length === 0,
    issues: cycles.map(cycle => ({
      severity: 'error',
      message: `Circular dependency: ${cycle.join(' -> ')}`,
      location: 'waves'
    }))
  };
}
```

### Step 5.4: Parseability Check (CRITICAL)

```typescript
// /execute skill MUST be able to parse this
function validateParseability(plan: ExecutionPlan): ValidationResult {
  try {
    // Simulate /execute parsing
    const parsed = parseExecutionPlan(plan);
    const waveStructure = extractWaveStructure(parsed);
    const storyStructure = extractStoryStructure(parsed);

    return {
      passed: true,
      issues: []
    };
  } catch (error) {
    return {
      passed: false,
      issues: [{
        severity: 'critical',
        message: `Parse error: ${error.message}`,
        location: 'GRANULAR_EXECUTION_PLAN.md'
      }]
    };
  }
}
```

### Step 5.5: Generate Validation Summary

**Location**: `docs/planning/VALIDATION_SUMMARY.md`

```markdown
# Validation Summary

## Overall Result: PASS ✓

## Evidence Alignment
- Verified claims: 42/42 (100%)
- Unverified claims: 0
- Result: ✓ PASS

## Completeness
- Required fields: 4/4 present
- Optional fields: 8/10 present
- Result: ✓ PASS

## Dependencies
- Total waves: 5
- Dependency layers: 3
- Circular dependencies: 0
- Result: ✓ PASS

## Parseability
- YAML structure: ✓ Valid
- Schema compliance: ✓ Valid
- /execute compatibility: ✓ Valid
- Result: ✓ PASS

## Issues
None

## Recommendations
Plan is ready for execution. Run /execute skill to begin implementation.
```

---

## Phase 6: User Approval

### Present Plan Summary

```markdown
# Execution Plan Ready

## Overview
- **Project**: [project-name]
- **Stories**: 12 stories across 5 waves
- **Estimated time**: 6-8 hours
- **Complexity**: Medium

## Wave Structure
1. **Wave 0.1**: Foundation Setup (2 stories, 60 min)
2. **Wave 0.2**: Core Feature Implementation (4 stories, 180 min)
3. **Wave 0.3**: Testing & QA (3 stories, 90 min)
4. **Wave 0.4**: Documentation (2 stories, 60 min)
5. **Wave 0.5**: Integration (1 story, 30 min)

## Quality Gates
- TypeScript: 0 errors required
- Lint: Must pass
- Tests: ≥80% coverage required

## Evidence Summary
- Research sources: 8 verified
- Best practices: 12 applied
- Risk mitigations: 5 identified

## Validation Result
✓ All checks passed

## Next Steps
1. Review the generated files:
   - docs/planning/execution/GRANULAR_EXECUTION_PLAN.md
   - docs/planning/tasks.json
   - docs/planning/VALIDATION_SUMMARY.md

2. If approved, run /execute to begin implementation

3. If changes needed, run /plan again with refinements

**Proceed with execution?**
```

---

## Quality Standards

### Evidence Quality

- **Verified**: Source URL or document reference
- **Confidence**: 0.0-1.0 score on claim reliability
- **Recency**: Prefer sources from last 12 months
- **Authority**: Official documentation > Blog posts > Forums

### Plan Quality

- **Completeness**: All required fields present
- **Consistency**: No contradictions in plan
- **Feasibility**: Technical implementation possible
- **Traceability**: All decisions traceable to evidence

### YAML Quality

- **Valid YAML**: Must parse without errors
- **Schema Compliance**: Must match execution_metadata.schema
- **Human Readable**: Proper indentation and comments
- **Version Control**: Include version and timestamp

---

## Integration with /execute Skill

### Handoff Protocol

When /plan completes successfully:

```bash
# /execute skill reads these files:
docs/planning/execution/GRANULAR_EXECUTION_PLAN.md  # Primary input
docs/planning/tasks.json                             # Machine-readable
docs/planning/VALIDATION_SUMMARY.md                  # Quality assurance
```

### /execute Validation

/execute skill will:

1. Parse GRANULAR_EXECUTION_PLAN.md
2. Validate wave structure
3. Check story dependencies
4. Enforce maxConcurrent limits via ResourceManager
5. Execute stories via WaveOrchestrator
6. Enforce quality gates

---

## Error Handling

### Intake Errors

| Error | Recovery |
|-------|----------|
| No user query | Prompt for query |
| Q&A timeout | Use defaults, mark as assumption |
| Conflicting answers | Ask follow-up question |

### Research Errors

| Error | Recovery |
|-------|----------|
| Agent crash | Spawn replacement agent |
| Resource limit exceeded | Sequential research (slower) |
| No evidence found | Mark as assumption, flag risk |

### Validation Errors

| Error | Recovery |
|-------|----------|
| Parse error | Fix YAML, re-validate |
| Circular dependency | Re-organize waves |
| Missing field | Add field or mark optional |

---

## File Structure After /plan

```
project/
├── docs/
│   └── planning/
│       ├── execution/
│       │   └── GRANULAR_EXECUTION_PLAN.md
│       ├── specs/
│       │   ├── component-specs.md
│       │   ├── integration-specs.md
│       │   └── data-models.md
│       ├── tasks.json
│       ├── RESEARCH_FINDINGS.md
│       └── VALIDATION_SUMMARY.md
└── .claude/
    └── skills/
        └── plan/
            └── SKILL.md
```

---

## Performance Targets

| Phase | Target |
|-------|--------|
| Intake (Q&A) | <5 minutes (simple), <15 minutes (complex) |
| Research | <30 minutes (all agents) |
| Specification | <10 minutes |
| Plan Generation | <10 minutes |
| Validation | <2 minutes |
| **Total** | **<60 minutes** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-06 | Initial hybrid /plan skill |

---

**Maintained by**: Rad Engineering Platform
**Last Updated**: 2026-01-06
**Status**: Active Development
