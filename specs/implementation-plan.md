# Technical Implementation Plan
## Automaton Auditor - Digital Courtroom System

## Tech Stack Overview

### Core Framework
- **LangGraph (StateGraph)**: Primary orchestration framework for multi-agent workflows
  - Enables parallel fan-out/fan-in execution patterns
  - Provides typed state management with reducers
  - Supports conditional edges for error handling
  - Version: `>=0.0.40`

### Runtime & Package Management
- **Python 3.11+**: Required for modern type hints and performance
- **uv**: Fast Python package manager and project manager
  - Handles dependency resolution and locking
  - Provides isolated virtual environments
  - Faster than pip for large dependency trees

### Type Safety & Data Models
- **Pydantic 2.5+**: Data validation and serialization
  - `BaseModel` for Evidence, JudicialOpinion, AuditReport
  - Field validation with constraints (score ranges, confidence bounds)
  - JSON schema generation for structured LLM outputs
- **TypedDict**: For AgentState with Annotated reducers
  - `operator.ior` for dictionary merging (evidences)
  - `operator.add` for list concatenation (opinions)

### LLM Integration
- **LangChain Core**: Base abstractions for LLM interactions
- **LangChain OpenAI**: Integration with GPT models
  - GPT-4o for judges (Layer 2) - high-quality reasoning
  - GPT-4o-mini for detectives (Layer 1) - cost-effective fact collection
- **LangChain Google GenAI**: Optional integration for vision models
  - Gemini Pro Vision for diagram analysis (VisionInspector)

### Repository Analysis
- **GitPython**: Safe git operations
  - Repository cloning with authentication handling
  - Git log extraction for forensic analysis
  - Version: `>=3.1.40`
- **Python AST Module**: Built-in code structure analysis
  - No external dependencies for AST parsing
  - Verifies StateGraph instantiation
  - Checks for Pydantic models and reducers
  - Validates parallel edge patterns

### Document Processing
- **Docling**: Primary PDF parsing library
  - Better structure preservation than basic PDF readers
  - Handles complex layouts and tables
  - Version: `>=1.0.0`
- **PyPDF**: Fallback PDF parser
  - Used when Docling unavailable
  - Basic text extraction
  - Version: `>=3.17.0`
- **Pillow**: Image processing for diagram extraction
  - Extracts images from PDFs for vision analysis
  - Version: `>=10.0.0`

### Observability
- **LangSmith**: Tracing and monitoring
  - Automatic tracing via `LANGCHAIN_TRACING_V2=true`
  - Custom tool traces with `@traceable` decorator
  - Project-level organization for audit runs

### Environment Management
- **python-dotenv**: Secure environment variable loading
  - API keys stored in `.env` (gitignored)
  - No hardcoded secrets
  - Version: `>=1.0.0`

## Architecture Decisions

### 1. Hierarchical StateGraph Pattern
**Choice**: Three-layer architecture with explicit fan-out/fan-in
- **Rationale**: Fixed workflow, no dynamic routing needed. Simpler to debug and trace.
- **Implementation**: 
  - Layer 0: `context_builder` (sequential)
  - Layer 1: Three detectives in parallel → `evidence_aggregator` (fan-in)
  - Layer 2: Three judges in parallel → `chief_justice` (fan-in)
  - Layer 3: `chief_justice` (sequential)

### 2. TypedDict State with Reducers
**Choice**: Shared TypedDict state over message passing
- **Rationale**: Structured data models, not chat messages. Native LangGraph pattern.
- **Implementation**:
  ```python
  evidences: Annotated[Dict[str, List[Evidence]], operator.ior]
  opinions: Annotated[List[JudicialOpinion], operator.add]
  ```

### 3. AST Over Regex for Code Analysis
**Choice**: Python's `ast` module for all code structure verification
- **Rationale**: Structural understanding. Rubric penalizes regex (Score 3 vs Score 5).
- **Implementation**: Custom AST visitors for StateGraph, Pydantic, reducer detection

### 4. Sandboxed Git Operations
**Choice**: `tempfile.TemporaryDirectory()` for all repository cloning
- **Rationale**: Security requirement. Prevents code injection and directory pollution.
- **Implementation**: `RepoInvestigator` class with automatic cleanup

### 5. Structured Output Enforcement
**Choice**: `.with_structured_output(Pydantic)` for all judge LLMs
- **Rationale**: Prevents hallucinations. Guarantees valid JSON matching JudicialOpinion schema.
- **Implementation**: Wrapped LLM calls with retry logic on ValidationError

### 6. Deterministic Synthesis Rules
**Choice**: Hardcoded Python if/else logic, not LLM-based averaging
- **Rationale**: Reproducible, auditable. Rubric awards Score 5 for deterministic rules.
- **Implementation**: `_synthesize_score()` function with named rules (security_override, fact_supremacy, etc.)

### 7. Per-Layer Model Configuration
**Choice**: Environment variables for model selection per layer
- **Rationale**: Cost optimization. Detectives can use cheaper models, judges need high quality.
- **Implementation**: `get_llm(layer: str)` factory function reading from env vars

## File Structure

```
automaton-auditor/
├── src/
│   ├── __init__.py
│   ├── config.py              # Model factory, env var loading
│   ├── state.py               # AgentState, Evidence, JudicialOpinion, AuditReport
│   ├── graph.py               # StateGraph definition, build + run
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── detectives.py      # context_builder, 3 detectives, aggregator
│   │   ├── judges.py          # make_judge_node factory, 3 personas
│   │   └── justice.py         # chief_justice, synthesis rules, report gen
│   └── tools/
│       ├── __init__.py
│       ├── repo_tools.py      # safe_clone, extract_git_history, AST analyzers
│       └── doc_tools.py       # ingest_pdf, search_keywords, extract_images
├── rubric/
│   └── week2_rubric.json      # Machine-readable constitution
├── audit/
│   ├── report_bypeer_received/
│   ├── report_onpeer_generated/
│   └── report_onself_generated/
├── .specify/                  # Spec kit configuration
├── specs/                     # Product specifications
├── .env                       # API keys (gitignored)
├── pyproject.toml            # uv project config
└── README.md                 # Setup and usage
```

## Implementation Constraints

### Required Patterns
- ✅ LangGraph StateGraph (not CrewAI, AutoGen, etc.)
- ✅ Pydantic BaseModel for all data structures
- ✅ AST parsing for code analysis (not regex)
- ✅ `tempfile` for sandboxed cloning
- ✅ LangSmith tracing for observability
- ✅ `uv` as package manager

### Forbidden Patterns
- ❌ `os.system()` - Use `subprocess.run()` with `shell=False`
- ❌ Regex for code structure - Use AST parsing
- ❌ Fixed clone directories - Use `tempfile.TemporaryDirectory()`
- ❌ Freeform text from judges - Must use Pydantic validation
- ❌ Linear graph flow - Must implement parallel execution

## Security Considerations

1. **Sandboxing**: All git operations in temporary directories
2. **Input Validation**: Sanitize repository URLs and file paths
3. **No Shell Injection**: Use `subprocess.run([], shell=False)`
4. **Secret Management**: API keys in `.env`, never committed
5. **Error Handling**: Graceful degradation, never expose sensitive info

## Performance Targets

- **Repository Cloning**: < 60 seconds
- **PDF Parsing**: Handle reports up to 50 pages
- **Graph Execution**: Complete audit within 5 minutes for standard repos
- **Memory Efficiency**: Clean up temporary directories after use

## Dependencies Summary

### Core Dependencies
```toml
langchain >= 0.1.0
langchain-core >= 0.1.0
langchain-openai >= 0.0.5
langgraph >= 0.0.40
pydantic >= 2.5.0
python-dotenv >= 1.0.0
```

### Analysis Dependencies
```toml
gitpython >= 3.1.40
docling >= 1.0.0
pypdf >= 3.17.0
pillow >= 10.0.0
```

### Optional Dependencies
```toml
langchain-google-genai >= 0.0.6  # For vision models
```

## Development Workflow

1. **Specification-Driven**: Code must align with `specs/` and `doc/Architecture.MD`
2. **Type Safety**: All functions must have type hints
3. **Testing**: Unit tests for tools, integration tests for graph
4. **Documentation**: ADR format for architectural decisions
5. **Observability**: All operations traceable via LangSmith

## Configuration Management

### Environment Variables
```bash
# IMPORTANT: These are PLACEHOLDERS only. Copy .env.example to .env and fill in your actual keys.
OPENAI_API_KEY=your_openai_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=automaton-auditor
LAYER1_MODEL=gpt-4o-mini
LAYER2_MODEL=gpt-4o
```

### Rubric Configuration
- Stored in `rubric/week2_rubric.json`
- Machine-readable JSON format
- Loaded once at graph creation
- Distributed via state to all nodes

## Output Format

- **Markdown Reports**: Structured, reproducible format
- **Metadata**: Git commit hash, model versions, timestamps
- **Traceability**: All evidence locations cited
- **Actionability**: File-level remediation instructions

