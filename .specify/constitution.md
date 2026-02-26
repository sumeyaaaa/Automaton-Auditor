# Automaton Auditor - Development Constitution

## Project Principles

This document establishes the governing principles and development guidelines for the Automaton Auditor project. All code, specifications, and architectural decisions must align with these principles.

## Core Principles

### 1. Production-Grade Quality
- **No Toy Models**: This is production infrastructure, not a proof-of-concept
- **Type Safety**: All state must use Pydantic models and TypedDict with proper reducers
- **Error Handling**: Graceful degradation, never silent failures
- **Observability**: All operations must be traceable via LangSmith

### 2. Forensic Accuracy
- **Evidence-Based**: All claims must be backed by objective evidence
- **AST Over Regex**: Use Python's `ast` module for code analysis, never regex
- **Sandboxed Operations**: All external operations (git clone, file I/O) must be sandboxed
- **No Hallucinations**: Cross-reference all documentation claims against actual codebase

### 3. Separation of Concerns
- **Detectives**: Collect facts only (no opinions, no scores)
- **Judges**: Interpret evidence and assign scores
- **Chief Justice**: Synthesize using deterministic rules only
- **Clear Boundaries**: Each layer has distinct responsibilities

### 4. Deterministic Behavior
- **Reproducible Scores**: Synthesis rules must be hardcoded, not LLM-based
- **Traceable Decisions**: All score assignments must cite specific evidence
- **Version Control**: Git commit hashes must be captured and reported
- **No Randomness**: Temperature 0 for all scoring LLMs

### 5. Security First
- **Sandboxing**: All git operations in `tempfile.TemporaryDirectory()`
- **No Shell Injection**: Use `subprocess.run()` with `shell=False`
- **Input Validation**: Sanitize all repository URLs and file paths
- **Error Handling**: Graceful handling of authentication failures

### 6. Parallel Execution
- **True Parallelism**: Detectives and judges must run in parallel, not sequentially
- **State Reducers**: Use `operator.ior` for dicts, `operator.add` for lists
- **Fan-Out/Fan-In**: Proper synchronization nodes between parallel layers
- **No Data Loss**: Reducers prevent parallel agents from overwriting data

## Code Quality Standards

### Type Safety
- ✅ Use Pydantic `BaseModel` for all data structures
- ✅ Use `TypedDict` for state with `Annotated` reducers
- ✅ Type hints required for all function signatures
- ❌ No plain Python dicts for complex nested structures

### Testing Standards
- Unit tests for all forensic tools
- Integration tests for graph execution
- Mock external dependencies (git, PDF parsing)
- Test parallel execution and state reducers

### Documentation Standards
- Docstrings for all public functions and classes
- Architecture decisions documented in ADR format
- Inline comments for complex logic
- README must include setup and usage instructions

## Architecture Constraints

### Required Patterns
- **LangGraph StateGraph**: Must use StateGraph, not other frameworks
- **Parallel Fan-Out/Fan-In**: Detectives and judges must run in parallel
- **Structured Output**: All judge LLMs must use `.with_structured_output()`
- **AST Parsing**: Code analysis must use `ast` module, not regex

### Forbidden Patterns
- ❌ `os.system()` - Use `subprocess.run()` instead
- ❌ Regex for code structure - Use AST parsing
- ❌ Fixed clone directories - Use `tempfile.TemporaryDirectory()`
- ❌ Freeform text from judges - Must use Pydantic validation
- ❌ Linear graph flow - Must implement parallel execution

## Performance Requirements

- **Repository Cloning**: Must complete within 60 seconds
- **PDF Parsing**: Must handle reports up to 50 pages
- **Graph Execution**: Complete audit within 5 minutes for standard repos
- **Memory Efficiency**: Clean up temporary directories after use

## User Experience Consistency

### Report Format
- Consistent Markdown structure across all audits
- Executive summary always first
- Per-criterion breakdown with consistent sections
- Remediation plan prioritized by severity

### Error Messages
- Clear, actionable error messages
- Include context (which file, which operation)
- Suggest remediation steps
- Never expose sensitive information (API keys, paths)

## Development Workflow

### Git Practices
- Atomic commits with clear messages
- Branch per feature
- PRs must include:
  - Description of changes
  - Test coverage
  - Updated documentation if needed

### Dependency Management
- Use `uv` as package manager
- Lock dependencies in `pyproject.toml`
- Document all external dependencies
- Keep dependencies minimal and focused

### Specification-Driven
- Architecture decisions documented in `doc/Architecture.MD`
- Specifications in `specs/` directory
- Code must align with specifications
- Update specs when architecture changes

## Compliance Requirements

- **Security**: No hardcoded API keys, use `.env` files
- **Licensing**: All dependencies must be compatible
- **Accessibility**: Error messages must be clear and actionable
- **Observability**: All operations must be traceable

## Review Criteria

All code changes must be reviewed against:
1. ✅ Alignment with core principles
2. ✅ Type safety and error handling
3. ✅ Test coverage
4. ✅ Documentation completeness
5. ✅ Security best practices
6. ✅ Performance impact

## Evolution

This constitution is a living document. As the project evolves:
- Principles may be refined based on learnings
- New constraints may be added for emerging patterns
- Decisions must be documented in Architecture.MD ADR section

---

**Last Updated**: 2025-02-25  
**Version**: 1.0.0




