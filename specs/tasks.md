# Implementation Tasks Breakdown
## Automaton Auditor - Digital Courtroom System

This document breaks down the technical implementation plan into actionable, prioritized tasks with dependencies.

## Task Categories

### Phase 1: Foundation & Infrastructure (Priority: Critical)
### Phase 2: Detective Layer Implementation (Priority: High)
### Phase 3: Judicial Layer Implementation (Priority: High)
### Phase 4: Synthesis & Reporting (Priority: High)
### Phase 5: Integration & Testing (Priority: Medium)
### Phase 6: Documentation & Polish (Priority: Low)

---

## Phase 1: Foundation & Infrastructure

### Task 1.1: Project Setup
**Status**: ✅ Complete
**Dependencies**: None
**Description**: 
- Initialize project with `uv`
- Create `pyproject.toml` with all dependencies
- Set up `.env.example` with required environment variables
- Create directory structure (`src/`, `specs/`, `audit/`, `rubric/`)

**Acceptance Criteria**:
- [x] `pyproject.toml` includes all required dependencies
- [x] Directory structure matches Architecture.MD
- [x] `.env.example` documents all API keys needed

### Task 1.2: State Definitions
**Status**: ✅ Complete
**Dependencies**: Task 1.1
**Description**:
- Create `src/state.py` with Pydantic models
- Define `Evidence`, `JudicialOpinion`, `CriterionResult`, `AuditReport`
- Define `AgentState` TypedDict with Annotated reducers
- Ensure proper type hints and field constraints

**Acceptance Criteria**:
- [x] All Pydantic models have proper Field descriptions
- [x] `AgentState` uses `operator.ior` for evidences dict
- [x] `AgentState` uses `operator.add` for opinions list
- [x] Score constraints (1-5) enforced
- [x] Confidence bounds (0.0-1.0) enforced

### Task 1.3: Configuration Management
**Status**: ⚠️ Partial
**Dependencies**: Task 1.1
**Description**:
- Create `src/config.py` with model factory function
- Implement `get_llm(layer: str)` that reads from env vars
- Support per-layer model configuration
- Handle missing API keys gracefully

**Acceptance Criteria**:
- [ ] `get_llm("layer1")` returns configured detective model
- [ ] `get_llm("layer2")` returns configured judge model
- [ ] Environment variables properly loaded via `python-dotenv`
- [ ] Error handling for missing API keys

### Task 1.4: Rubric Loading
**Status**: ✅ Complete
**Dependencies**: Task 1.1
**Description**:
- Create `rubric/week2_rubric.json` (or use existing `rubric.json`)
- Implement rubric loading function in `src/graph.py`
- Validate JSON structure on load
- Distribute rubric dimensions to state

**Acceptance Criteria**:
- [x] Rubric JSON follows specification format
- [x] Loading function handles missing file errors
- [x] Rubric dimensions accessible in state

---

## Phase 2: Detective Layer Implementation

### Task 2.1: Repository Investigation Tools
**Status**: ✅ Complete
**Dependencies**: Task 1.2
**Description**:
- Create `src/tools/repo_tools.py`
- Implement `RepoInvestigator` class with sandboxed cloning
- Implement `extract_git_history()` for commit analysis
- Implement AST-based analyzers:
  - `analyze_graph_structure()` - StateGraph detection
  - `check_state_management()` - Pydantic/TypedDict verification
  - `check_structured_output()` - Judge validation
  - `check_sandboxing()` - Security verification

**Acceptance Criteria**:
- [x] Git cloning uses `tempfile.TemporaryDirectory()`
- [x] No `os.system()` calls
- [x] AST parsing (not regex) for all code analysis
- [x] Proper error handling for authentication failures
- [x] Cleanup of temporary directories

### Task 2.2: Document Analysis Tools
**Status**: ✅ Complete
**Dependencies**: Task 1.2
**Description**:
- Create `src/tools/doc_tools.py`
- Implement `DocAnalyst` class with PDF parsing
- Implement `ingest_pdf()` with chunking (RAG-lite)
- Implement `search_keywords()` for theoretical depth
- Implement `extract_file_paths()` and `cross_reference_files()`
- Implement `VisionInspector` for diagram analysis (optional)

**Acceptance Criteria**:
- [x] PDF parsing with Docling (fallback to PyPDF)
- [x] Text chunking for efficient querying
- [x] Keyword search with context extraction
- [x] File path extraction and cross-referencing
- [x] Image extraction from PDFs

### Task 2.3: Detective Nodes
**Status**: ✅ Complete
**Dependencies**: Task 2.1, Task 2.2
**Description**:
- Create `src/nodes/detectives.py`
- Implement `repo_investigator_node()` - collects repo evidence
- Implement `doc_analyst_node()` - collects PDF evidence
- Implement `vision_inspector_node()` - collects diagram evidence
- Implement `evidence_aggregator_node()` - cross-references and merges

**Acceptance Criteria**:
- [x] Each detective filters rubric by `target_artifact`
- [x] Evidence objects properly structured with confidence scores
- [x] Evidence aggregator performs cross-referencing
- [x] Hallucination detection (claimed files that don't exist)
- [x] All evidence merged via `operator.ior` reducer

---

## Phase 3: Judicial Layer Implementation

### Task 3.1: Judge Node Factory
**Status**: ✅ Complete
**Dependencies**: Task 1.2, Task 1.3
**Description**:
- Create `src/nodes/judges.py`
- Implement distinct persona system prompts:
  - Prosecutor: "Trust No One. Assume Vibe Coding."
  - Defense: "Reward Effort and Intent."
  - Tech Lead: "Does It Work? Is It Maintainable?"
- Implement `prosecutor_node()`, `defense_node()`, `tech_lead_node()`
- Use `.with_structured_output(JudicialOpinion)` for all LLM calls

**Acceptance Criteria**:
- [x] Three distinct personas with conflicting philosophies
- [x] All judges iterate over all rubric dimensions
- [x] Structured output enforced (Pydantic validation)
- [x] Evidence citations included in opinions
- [x] Error handling for validation failures

### Task 3.2: Judge Prompt Engineering
**Status**: ✅ Complete
**Dependencies**: Task 3.1
**Description**:
- Design system prompts for each persona
- Include rubric scoring guidelines in prompts
- Ensure prompts generate distinct opinions
- Test for persona separation (no collusion)

**Acceptance Criteria**:
- [x] Prosecutor prompts focus on gaps and security
- [x] Defense prompts focus on effort and intent
- [x] Tech Lead prompts focus on functionality
- [x] Prompts share < 50% text (persona separation)
- [x] Temperature 0 for deterministic scoring

---

## Phase 4: Synthesis & Reporting

### Task 4.1: Chief Justice Synthesis Engine
**Status**: ✅ Complete
**Dependencies**: Task 3.1
**Description**:
- Create `src/nodes/justice.py`
- Implement `chief_justice_node()` with deterministic rules:
  - Security Override: Cap score at 3 for vulnerabilities
  - Fact Supremacy: Evidence overrules opinion
  - Functionality Weight: Tech Lead carries weight for architecture
  - Variance Re-evaluation: Handle high disagreement
- Implement `_synthesize_score()` with hardcoded logic
- Generate dissent summaries for variance > 2

**Acceptance Criteria**:
- [x] Deterministic Python if/else logic (not LLM averaging)
- [x] Named rules (security_override, fact_supremacy, etc.)
- [x] Score variance triggers re-evaluation
- [x] Dissent summaries generated when applicable
- [x] All rules documented and testable

### Task 4.2: Report Generation
**Status**: ✅ Complete
**Dependencies**: Task 4.1
**Description**:
- Implement `_serialize_report_to_markdown()` in `src/graph.py`
- Generate executive summary with overall score
- Generate per-criterion breakdown with:
  - Final synthesized score
  - All three judge opinions
  - Dissent summaries
  - Remediation instructions
- Generate comprehensive remediation plan

**Acceptance Criteria**:
- [x] Markdown format matches Architecture.MD specification
- [x] Executive summary includes metadata (commit hash, models)
- [x] All criterion sections complete
- [x] Remediation plan prioritized by severity
- [x] Reports saved to `audit/` directory

---

## Phase 5: Integration & Testing

### Task 5.1: Graph Orchestration
**Status**: ✅ Complete
**Dependencies**: Task 2.3, Task 3.1, Task 4.1
**Description**:
- Create `src/graph.py` with `create_auditor_graph()`
- Wire all nodes with proper edges:
  - START → context_builder
  - context_builder → [3 detectives in parallel]
  - [3 detectives] → evidence_aggregator (fan-in)
  - evidence_aggregator → [3 judges in parallel]
  - [3 judges] → chief_justice (fan-in)
  - chief_justice → END
- Implement `run_audit()` function

**Acceptance Criteria**:
- [x] Parallel fan-out for detectives
- [x] Parallel fan-out for judges
- [x] Proper fan-in synchronization
- [x] List-style join edges (not separate add_edge calls)
- [x] Graph compiles without errors

### Task 5.2: End-to-End Integration
**Status**: ⚠️ Partial
**Dependencies**: Task 5.1
**Description**:
- Test complete workflow from repo URL to report
- Verify state reducers prevent data overwrites
- Test error handling at each layer
- Verify LangSmith tracing works

**Acceptance Criteria**:
- [ ] Complete audit runs end-to-end
- [ ] State properly merged via reducers
- [ ] Errors handled gracefully
- [ ] LangSmith traces visible
- [ ] Reports generated correctly

### Task 5.3: Unit Testing
**Status**: ❌ Not Started
**Dependencies**: All previous tasks
**Description**:
- Write unit tests for all tools
- Test AST analyzers with sample code
- Test PDF parsing with sample documents
- Mock external dependencies (git, LLMs)

**Acceptance Criteria**:
- [ ] Test coverage for all tools
- [ ] AST analyzers tested with known code patterns
- [ ] PDF parsing tested with sample files
- [ ] All mocks properly configured

### Task 5.4: Integration Testing
**Status**: ❌ Not Started
**Dependencies**: Task 5.2
**Description**:
- Test graph execution with sample repository
- Verify parallel execution works correctly
- Test state reducer behavior
- Verify report generation

**Acceptance Criteria**:
- [ ] Graph executes with test repo
- [ ] Parallel nodes run concurrently
- [ ] State reducers merge correctly
- [ ] Reports match expected format

---

## Phase 6: Documentation & Polish

### Task 6.1: README Documentation
**Status**: ✅ Complete
**Dependencies**: Task 5.1
**Description**:
- Update `README.md` with setup instructions
- Document usage examples
- Include architecture diagram
- List all dependencies

**Acceptance Criteria**:
- [x] Clear setup instructions
- [x] Usage examples provided
- [x] Architecture overview included
- [x] Dependencies documented

### Task 6.2: Code Documentation
**Status**: ⚠️ Partial
**Dependencies**: All implementation tasks
**Description**:
- Add docstrings to all public functions
- Document complex logic with inline comments
- Ensure type hints are complete

**Acceptance Criteria**:
- [x] All public functions have docstrings
- [ ] Complex logic documented
- [x] Type hints complete

### Task 6.3: Architecture Documentation
**Status**: ✅ Complete
**Dependencies**: None
**Description**:
- Maintain `doc/Architecture.MD` with ADRs
- Document all architectural decisions
- Keep specification aligned with implementation

**Acceptance Criteria**:
- [x] Architecture.MD up to date
- [x] ADRs documented
- [x] Specs align with code

---

## Task Priority Summary

### Critical Path (Must Complete First)
1. Task 1.2: State Definitions ✅
2. Task 1.3: Configuration Management ⚠️
3. Task 2.1: Repository Investigation Tools ✅
4. Task 2.2: Document Analysis Tools ✅
5. Task 2.3: Detective Nodes ✅
6. Task 3.1: Judge Node Factory ✅
7. Task 4.1: Chief Justice Synthesis Engine ✅
8. Task 5.1: Graph Orchestration ✅

### High Priority (Complete for MVP)
- Task 3.2: Judge Prompt Engineering ✅
- Task 4.2: Report Generation ✅
- Task 5.2: End-to-End Integration ⚠️

### Medium Priority (Polish)
- Task 5.3: Unit Testing ❌
- Task 5.4: Integration Testing ❌

### Low Priority (Nice to Have)
- Task 6.1: README Documentation ✅
- Task 6.2: Code Documentation ⚠️
- Task 6.3: Architecture Documentation ✅

---

## Implementation Status

**Overall Progress**: ~85% Complete

- ✅ **Complete**: 12 tasks
- ⚠️ **Partial**: 3 tasks
- ❌ **Not Started**: 2 tasks

**Remaining Work**:
1. Complete configuration management (Task 1.3)
2. Finish end-to-end integration testing (Task 5.2)
3. Add unit tests (Task 5.3)
4. Add integration tests (Task 5.4)
5. Complete code documentation (Task 6.2)

