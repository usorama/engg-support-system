# STORY-020: Multi-Language AST Parsing

**Priority**: P1 - High
**Status**: PLANNED
**Created**: 2025-12-31
**Dependencies**: STORY-019 (Autonomous Watcher)

---

## Problem Statement

The current multi-language support uses **regex-based extraction** which has significant limitations:

1. **No actual AST parsing for TypeScript/JS** - Misses complex patterns like arrow functions in nested objects, HOCs, and dynamic exports
2. **No call graph for non-Python** - `CALLS` relationships not extracted for TypeScript/JavaScript
3. **Incomplete import/dependency tracking** - Python imports parsed, but JS/TS `import` statements not fully mapped to graph relationships
4. **No cross-language relationships** - If Python calls a TypeScript API (or vice versa), that link isn't captured
5. **Regex patterns incomplete** - Edge cases like decorators, generics, conditional exports, and template literals may be missed

**Business Impact**: The knowledge graph provides incomplete context for polyglot codebases, reducing query accuracy and missing architectural relationships.

---

## Lessons Learned (from STORY-019)

| Issue | Root Cause | Resolution |
|-------|------------|------------|
| Hardcoded Python assumption | `build_graph.py:670` checked `f.endswith(".py")` | Fixed with `CODE_EXTENSIONS` set |
| Config not consumed | `file_patterns` in `projects.yaml` was ignored | Now used in file discovery |
| AST is language-specific | Python's `ast.parse()` only works for Python | Added regex fallback (this story improves it) |

---

## Success Criteria

1. TypeScript/JavaScript files parsed with proper AST (not regex)
2. `CALLS` relationships extracted for JS/TS function invocations
3. `IMPORTS` relationships captured for all `import`/`require` statements
4. Cross-language API boundaries detected (e.g., Python FastAPI → TypeScript fetch)
5. 90%+ extraction accuracy on sample codebases (pinglearn, veracity-engine)
6. No performance regression (indexing time within 2x of regex approach)

---

## Technical Design

### Architecture Options

#### Option A: tree-sitter (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                    build_graph.py                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  Python Parser   │    │  Tree-sitter     │               │
│  │  (ast.parse)     │    │  Parser          │               │
│  │                  │    │                  │               │
│  │  .py files       │    │  .ts .js .go     │               │
│  │                  │    │  .java .rs etc   │               │
│  └────────┬─────────┘    └────────┬─────────┘               │
│           │                       │                          │
│           └───────────┬───────────┘                          │
│                       ▼                                      │
│           ┌──────────────────────┐                          │
│           │   Unified AST Model  │                          │
│           │   (language-agnostic)│                          │
│           └──────────┬───────────┘                          │
│                      ▼                                       │
│           ┌──────────────────────┐                          │
│           │      Neo4j KG        │                          │
│           └──────────────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Pros**:
- Single library supports 100+ languages
- Incremental parsing (fast re-indexing)
- Battle-tested (used by GitHub, Neovim, Helix)
- Python bindings available (`tree-sitter` package)

**Cons**:
- Requires grammar files per language
- Learning curve for query syntax

#### Option B: ts-morph (TypeScript-specific)

**Pros**:
- Full TypeScript type information
- Excellent API for TS/JS specifically

**Cons**:
- TypeScript/JavaScript only
- Requires Node.js subprocess or JS runtime

#### Option C: Language Server Protocol (LSP)

**Pros**:
- Leverages existing language servers
- Type information included

**Cons**:
- Heavy dependency (need running servers)
- Complex orchestration

### Recommended: Hybrid Approach

1. **Python**: Continue using `ast.parse()` (already works)
2. **TypeScript/JavaScript**: Use `tree-sitter-typescript` and `tree-sitter-javascript`
3. **Other languages**: Use tree-sitter with appropriate grammars
4. **Fallback**: Keep regex for unsupported languages

### Unified AST Model

```python
@dataclass
class UnifiedNode:
    """Language-agnostic AST node representation."""
    kind: str  # 'function', 'class', 'method', 'interface', 'type'
    name: str
    qualified_name: str
    file_path: str
    start_line: int
    end_line: int
    docstring: Optional[str]
    parameters: List[str]
    return_type: Optional[str]
    decorators: List[str]
    modifiers: List[str]  # 'export', 'async', 'static', 'public', etc.
    language: str

@dataclass
class UnifiedEdge:
    """Language-agnostic relationship representation."""
    source: str  # qualified_name
    target: str  # qualified_name or module path
    kind: str    # 'CALLS', 'IMPORTS', 'EXTENDS', 'IMPLEMENTS'
    file_path: str
    line: int
```

---

## Implementation Plan

### Phase 1: Tree-sitter Integration (4 hours)

1. Add `tree-sitter` and language grammars to requirements
2. Create `core/parsers/tree_sitter_parser.py`
3. Implement TypeScript/JavaScript parsing
4. Extract functions, classes, interfaces, types
5. Unit tests for TS/JS extraction

### Phase 2: Call Graph Extraction (3 hours)

1. Parse function call expressions in tree-sitter
2. Resolve call targets (local, imported, method calls)
3. Create `CALLS` relationships in Neo4j
4. Handle async/await patterns
5. Tests for call graph accuracy

### Phase 3: Import/Dependency Mapping (2 hours)

1. Parse `import`/`require`/`export` statements
2. Resolve relative and absolute imports
3. Create `IMPORTS` relationships
4. Handle re-exports and barrel files
5. Tests for import resolution

### Phase 4: Cross-Language Detection (2 hours)

1. Identify API boundary patterns:
   - Python FastAPI/Flask routes
   - TypeScript fetch/axios calls
   - OpenAPI/GraphQL schemas
2. Create `CROSS_LANG_CALLS` relationships
3. Tests for API boundary detection

### Phase 5: Additional Languages (2 hours)

1. Add Go parser (tree-sitter-go)
2. Add Java/Kotlin parser
3. Add Rust parser
4. Fallback to regex for unsupported languages

### Phase 6: Testing & Verification (2 hours)

1. Index pinglearn with new parsers
2. Compare node/edge counts vs regex approach
3. Verify query accuracy improvement
4. Performance benchmarking

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `core/parsers/__init__.py` | CREATE | Parser module initialization |
| `core/parsers/base.py` | CREATE | Abstract base parser class |
| `core/parsers/python_parser.py` | CREATE | Refactored Python AST parser |
| `core/parsers/tree_sitter_parser.py` | CREATE | Tree-sitter based multi-language parser |
| `core/parsers/unified_model.py` | CREATE | UnifiedNode and UnifiedEdge dataclasses |
| `core/build_graph.py` | MODIFY | Use parser factory instead of inline parsing |
| `requirements.txt` | MODIFY | Add tree-sitter dependencies |
| `tests/test_parsers.py` | CREATE | Parser unit tests |
| `tests/fixtures/sample_ts.ts` | CREATE | TypeScript test fixtures |
| `tests/fixtures/sample_go.go` | CREATE | Go test fixtures |

---

## Dependencies

```
tree-sitter>=0.21.0
tree-sitter-python>=0.21.0
tree-sitter-typescript>=0.21.0
tree-sitter-javascript>=0.21.0
tree-sitter-go>=0.21.0
tree-sitter-java>=0.21.0
tree-sitter-rust>=0.21.0
```

---

## Testing Checklist

- [ ] Tree-sitter parses TypeScript files without errors
- [ ] Functions, classes, interfaces extracted from TS/JS
- [ ] Arrow functions and HOCs captured correctly
- [ ] `CALLS` relationships created for function invocations
- [ ] `IMPORTS` relationships created for import statements
- [ ] Cross-language API calls detected
- [ ] Performance within 2x of regex approach
- [ ] All existing Python parsing tests still pass
- [ ] Query accuracy improved for pinglearn

---

## Definition of Done

1. TypeScript/JavaScript parsed with tree-sitter (not regex)
2. Call graph extracted for JS/TS with `CALLS` relationships
3. Import graph complete with `IMPORTS` relationships
4. Cross-language API boundaries detected
5. All tests pass
6. Query accuracy verified on pinglearn
7. Documentation updated

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tree-sitter grammar compatibility | Pin grammar versions, test on CI |
| Performance regression | Benchmark before/after, use incremental parsing |
| Edge cases in TS/JS | Comprehensive test fixtures from real codebases |
| Breaking existing Python parsing | Refactor behind abstraction, maintain backward compat |

---

## References

- [tree-sitter Python bindings](https://github.com/tree-sitter/py-tree-sitter)
- [tree-sitter TypeScript grammar](https://github.com/tree-sitter/tree-sitter-typescript)
- [ts-morph documentation](https://ts-morph.com/)
- [LSP specification](https://microsoft.github.io/language-server-protocol/)
