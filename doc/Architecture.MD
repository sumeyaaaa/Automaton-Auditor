# Architecture Specification
## Automaton Auditor — Digital Courtroom System

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Status** | Draft |
| **Author** | FDE Challenge Week 2 |
| **Framework** | LangGraph (StateGraph) |
| **Runtime** | Python 3.11+ |
| **Package Manager** | uv |

---

## 1. System Purpose

A hierarchical multi-agent system that audits code repositories and PDF reports against a machine-readable rubric. The system implements a three-layer Digital Courtroom: forensic evidence collection, dialectical judicial evaluation, and deterministic synthesis.

**Input:** GitHub repository URL + PDF report path
**Output:** Scored Markdown audit report with dissenting opinions and remediation plan

---

## 2. High-Level Architecture

```
                         ┌──────────────┐
                         │    START     │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │  context_    │  Superstep 1
                         │  builder     │  Load rubric → state
                         └──────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
       ┌──────▼──────┐  ┌──────▼───────┐  ┌──────▼──────┐
       │    repo_     │  │    doc_      │  │   vision_   │  Superstep 2
       │  detective   │  │  detective   │  │  detective  │  PARALLEL
       └──────┬───────┘  └──────┬───────┘  └──────┬──────┘
              │                 │                  │
              └─────────────────┼─────────────────┘
                                │
                         ┌──────▼───────┐
                         │  evidence_   │  Superstep 3
                         │  aggregator  │  Cross-reference + hallucination detection
                         └──────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
       ┌──────▼──────┐  ┌──────▼───────┐  ┌──────▼──────┐
       │  prosecutor  │  │   defense    │  │  tech_lead  │  Superstep 4
       │              │  │              │  │             │  PARALLEL
       └──────┬───────┘  └──────┬───────┘  └──────┬──────┘
              │                 │                  │
              └─────────────────┼─────────────────┘
                                │
                         ┌──────▼───────┐
                         │    chief_    │  Superstep 5
                         │   justice    │  Deterministic synthesis
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │     END      │
                         └──────────────┘
```

---

## 3. State Schema

### 3.1 AgentState

```python
class AgentState(TypedDict):
    repo_url: str                                          # Set at invoke
    pdf_path: str                                          # Set at invoke
    git_commit_hash: str                                   # Set by repo_detective
    model_metadata: Dict[str, str]                         # Set by context_builder
    rubric_dimensions: List[Dict]                          # Set by context_builder
    evidences: Annotated[Dict[str, List], operator.ior]    # Parallel: detectives
    opinions: Annotated[List, operator.add]                # Parallel: judges
    final_report: str                                      # Set by chief_justice
```

### 3.2 Reducer Rationale

| Field | Reducer | Parallel Writers | Merge Behavior |
|-------|---------|-----------------|----------------|
| `evidences` | `operator.ior` | 3 detectives | `{"repo": [...]} \| {"doc": [...]} \| {"vision": [...]}` → merged dict |
| `opinions` | `operator.add` | 3 judges | `[p1,p2] + [d1,d2] + [t1,t2]` → flat list |
| `final_report` | None | chief_justice only | Overwrite (no conflict) |

### 3.3 Evidence

```python
class Evidence(BaseModel):
    criterion_id: str          # Links to rubric dimension id
    goal: str                  # Forensic protocol executed
    found: bool                # Binary: artifact present or absent
    content: Optional[str]     # Code snippet, commit log, PDF excerpt
    location: str              # file:line, commit hash, or "not_found"
    rationale: str             # Why confident (AST confirmed, etc.)
    confidence: float          # 0.0–1.0, must be justified by rationale
```

**Constraint:** No `score`, `quality`, or `recommendation` fields. Detectives collect facts only.

### 3.4 JudicialOpinion

```python
class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str          # Must match rubric dimension id
    score: int                 # 1–5 integer
    argument: str              # Reasoning with specific file citations
    cited_evidence: List[str]  # Evidence locations referenced
```

**Constraint:** Enforced via `.with_structured_output(JudicialOpinion)`.

---

## 4. Node Specifications

### 4.1 Layer 0 — context_builder

| Property | Value |
|----------|-------|
| **Reads** | `repo_url`, `pdf_path` |
| **Writes** | `rubric_dimensions`, `model_metadata` |
| **LLM** | None |
| **Logic** | Load `rubric/week2_rubric.json`, write full dimensions list to state, populate model_metadata from config |

### 4.2 Layer 1 — Detectives

All three execute in a single superstep (parallel).

#### repo_detective

| Property | Value |
|----------|-------|
| **Reads** | `repo_url`, `rubric_dimensions` (filtered: `target_artifact == "github_repo"`) |
| **Writes** | `evidences["repo"]`, `git_commit_hash` |
| **LLM** | `get_llm("layer1")` — optional, for commit narrative analysis |
| **Tools** | `safe_clone`, `extract_git_history`, `check_stategraph`, `check_pydantic_models`, `check_parallel_edges`, `check_sandboxing`, `check_structured_output`, `check_security` |

**Forensic Protocols:**

| Protocol | Method | Evidence Goal |
|----------|--------|---------------|
| Git forensics | `subprocess.run(["git", "log", "--oneline", "--reverse"])` | Commit count, progression pattern |
| State rigor | `ast.walk` → `ast.ClassDef` with `BaseModel` base | Pydantic model existence |
| Graph wiring | `ast.walk` → `ast.Call` where attr == `add_edge` | Fan-out/fan-in detection |
| Safe tooling | `ast.walk` → check for `TemporaryDirectory`, flag `os.system`/`eval` | Security compliance |
| Structured output | `ast.walk` → check for `with_structured_output` attr | JSON enforcement |

#### doc_detective

| Property | Value |
|----------|-------|
| **Reads** | `pdf_path`, `rubric_dimensions` (filtered: `target_artifact == "pdf_report"`) |
| **Writes** | `evidences["doc"]` |
| **LLM** | `get_llm("layer1")` — for keyword context analysis |
| **Tools** | `ingest_pdf`, `search_keywords`, `extract_file_path_claims` |

**Forensic Protocols:**

| Protocol | Method | Evidence Goal |
|----------|--------|---------------|
| Keyword depth | Search for "Dialectical Synthesis", "Fan-In/Fan-Out", "Metacognition", "State Synchronization" | Explanatory context vs buzzword |
| File path claims | Regex extract paths like `src/...py` from PDF text | Claims to cross-reference |

#### vision_detective

| Property | Value |
|----------|-------|
| **Reads** | `pdf_path`, `rubric_dimensions` |
| **Writes** | `evidences["vision"]` |
| **LLM** | Multimodal `get_llm("layer1")` |
| **Tools** | `extract_images_from_pdf` |
| **Note** | Optional per challenge spec. Returns minimal evidence if no images found. |

#### evidence_aggregator

| Property | Value |
|----------|-------|
| **Reads** | `evidences` (all keys) |
| **Writes** | `evidences` (adds cross-reference entries) |
| **LLM** | None |
| **Logic** | Cross-reference doc claims against repo findings. Generate hallucination Evidence when report claims do not match repo evidence. |

**Cross-reference logic:**
```
FOR each file_path_claim in evidences["doc"]:
    IF file_path_claim.content NOT IN [e.location for e in evidences["repo"]]:
        CREATE Evidence(
            criterion_id="forensic_accuracy_docs",
            goal=f"HALLUCINATION: Report claims {path} exists",
            found=False,
            confidence=0.95
        )
```

### 4.3 Layer 2 — Judges

All three execute in a single superstep (parallel).

#### Shared Judge Architecture

All judges use a factory pattern:

```python
def make_judge_node(persona: str) -> Callable:
```

**Prompt structure:**

```
SYSTEM = JUDGE_BASE_PROMPT + PERSONA_OVERLAYS[persona]
USER   = criterion_info + judicial_logic[persona] + scoring_rubric + formatted_evidence
```

- Evidence placed LAST in user prompt (attention bias to start/end)
- Chain-of-thought: `argument` field required before `score`
- Temperature: 0 (deterministic scoring)

#### Persona Specifications

| Persona | Philosophy | Focus | Scoring Tendency |
|---------|-----------|-------|-----------------|
| **Prosecutor** | "Trust No One. Assume Vibe Coding." | Missing requirements, security flaws, shortcuts | 1–2 (harsh) |
| **Defense** | "Reward Effort and Intent." | Git struggle, creative workarounds, understanding | 4–5 (generous) |
| **TechLead** | "Does It Work? Is It Maintainable?" | Architecture soundness, reducer correctness | 2–4 (pragmatic, tiebreaker) |

#### Per-Judge Output

Each judge iterates over ALL `rubric_dimensions`, producing one `JudicialOpinion` per dimension. Total output: `N_criteria × 1` opinions per judge.

Evidence filtering per criterion:
```python
relevant = [e for src in state["evidences"].values()
            for e in src if e.criterion_id == criterion["id"]]
```

### 4.4 Layer 3 — Chief Justice

| Property | Value |
|----------|-------|
| **Reads** | `opinions`, `rubric_dimensions` |
| **Does NOT read** | `evidences` — trusts judges' interpretation |
| **Writes** | `final_report` |
| **LLM** | Optional for report narrative only. Scores are deterministic. |

---

## 5. Graph Wiring

### 5.1 Edge Definitions

```python
builder.add_edge(START, "context_builder")

# Layer 1 fan-out
builder.add_edge("context_builder", "repo_detective")
builder.add_edge("context_builder", "doc_detective")
builder.add_edge("context_builder", "vision_detective")

# Layer 1 fan-in (JOIN)
builder.add_edge(
    ["repo_detective", "doc_detective", "vision_detective"],
    "evidence_aggregator"
)

# Layer 2 fan-out
builder.add_edge("evidence_aggregator", "prosecutor")
builder.add_edge("evidence_aggregator", "defense")
builder.add_edge("evidence_aggregator", "tech_lead")

# Layer 2 fan-in (JOIN)
builder.add_edge(
    ["prosecutor", "defense", "tech_lead"],
    "chief_justice"
)

builder.add_edge("chief_justice", END)
```

### 5.2 Join Edge Constraint

Fan-in MUST use list syntax `add_edge([a, b, c], d)`. Separate `add_edge` calls to the same destination may cause it to execute multiple times.

### 5.3 Superstep Execution Order

| Step | Nodes | Mode |
|------|-------|------|
| 1 | `context_builder` | Sequential |
| 2 | `repo_detective`, `doc_detective`, `vision_detective` | Parallel |
| 3 | `evidence_aggregator` | Sequential |
| 4 | `prosecutor`, `defense`, `tech_lead` | Parallel |
| 5 | `chief_justice` | Sequential |

---

## 6. Scoring System

### 6.1 Rubric Dimensions

| ID | Name | Target Artifact | Primary Detective |
|----|------|----------------|-------------------|
| `forensic_accuracy_code` | Forensic Accuracy (Codebase) | `github_repo` | `repo_detective` |
| `forensic_accuracy_docs` | Forensic Accuracy (Documentation) | `pdf_report` | `doc_detective` |
| `judicial_nuance` | Judicial Nuance & Dialectics | `github_repo` | `repo_detective` |
| `langgraph_architecture` | LangGraph Orchestration Rigor | `github_repo` | `repo_detective` |

### 6.2 Score Scale

| Score | Label | Definition |
|-------|-------|-----------|
| 1 | Vibe Coder | Fundamentally broken or missing. Copy-paste without understanding. |
| 2 | Below Competent | Attempted but significant gaps. Wrong patterns, no parallelism. |
| 3 | Competent Orchestrator | Functional, meets basic requirements. Working graph, basic personas. |
| 4 | Above Competent | Solid work with advanced features. Proper reducers, clear debate. |
| 5 | Master Thinker | Exceptional. Full AST, deterministic synthesis, debate cycles. |

**Total: 4 criteria × 5 max = 20 points**

### 6.3 Scoring Method

Pointwise scoring via LLM-as-Judge with:
- Rubric-anchored descriptions per level (included in prompt)
- Chain-of-thought (argument before score)
- Evidence citation requirement
- Structured output enforcement (`.with_structured_output()`)
- Multi-judge ensemble (3 personas reduce individual bias)
- Temperature 0 for deterministic outputs

### 6.4 Synthesis Rules

Rules are **conditional triggers**, not sequential priority. Each fires independently when its condition is met.

```python
def apply_synthesis(p: JudicialOpinion, d: JudicialOpinion, t: JudicialOpinion):
    score = None
    rules = []

    # SECURITY OVERRIDE
    # When: Prosecutor flags security vulnerability with score <= 2
    if p.score <= 2 and "security" in p.argument.lower():
        score = min(3, t.score)
        rules.append("security_override")

    # FACT SUPREMACY
    # When: Prosecutor cites hallucination (report claims non-existent artifact)
    if "hallucination" in p.argument.lower() or "not found" in p.argument.lower():
        if score is None:
            score = p.score
        rules.append("fact_supremacy")

    # HIGH VARIANCE
    # When: Max - Min score spread > 2 points
    scores = [p.score, d.score, t.score]
    if max(scores) - min(scores) > 2:
        if score is None:
            score = t.score  # TechLead breaks tie
        rules.append("high_variance")

    # CONSENSUS (default)
    if score is None:
        score = round(p.score * 0.25 + d.score * 0.25 + t.score * 0.50)
        rules.append("consensus")

    return score, rules
```

Multiple rules can fire simultaneously. First rule that sets `score` wins. All triggered rules are logged for dissent.

---

## 7. Configuration

### 7.1 Environment Variables

```bash
# API Keys
OPENAI_API_KEY=sk-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=automaton-auditor

# Per-layer model config
LAYER1_MODEL=gpt-4o-mini
LAYER1_PROVIDER=openai
LAYER2_MODEL=gpt-4o
LAYER2_PROVIDER=openai
LAYER3_MODEL=gpt-4o
LAYER3_PROVIDER=openai
```

### 7.2 Model Factory

```python
# src/config.py
def get_llm(layer: str) -> BaseChatModel:
    config = MODEL_CONFIG[layer]
    if config["provider"] == "openai":
        return ChatOpenAI(model=config["model"], temperature=0)
    # Extend for anthropic, google, litellm
```

All nodes use `get_llm("layerN")` instead of hardcoded model strings.

---

## 8. Tool Specifications

### 8.1 Safety Constraints

| Forbidden | Required Alternative |
|-----------|---------------------|
| `os.system()` | `subprocess.run([], shell=False)` |
| Fixed clone directory | `tempfile.TemporaryDirectory()` |
| `eval()` / `exec()` | `ast.parse()` + `ast.walk()` |
| Regex for code structure | AST tree traversal |

### 8.2 Tool Registry

| Tool | File | Used By | Decorator |
|------|------|---------|-----------|
| `safe_clone` | `src/tools/git_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `extract_git_history` | `src/tools/git_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `check_stategraph` | `src/tools/ast_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `check_pydantic_models` | `src/tools/ast_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `check_parallel_edges` | `src/tools/ast_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `check_sandboxing` | `src/tools/ast_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `check_structured_output` | `src/tools/ast_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `check_security` | `src/tools/ast_tools.py` | `repo_detective` | `@traceable(run_type="tool")` |
| `ingest_pdf` | `src/tools/pdf_tools.py` | `doc_detective` | `@traceable(run_type="tool")` |
| `search_keywords` | `src/tools/pdf_tools.py` | `doc_detective` | `@traceable(run_type="tool")` |
| `extract_images_from_pdf` | `src/tools/pdf_tools.py` | `vision_detective` | `@traceable(run_type="tool")` |

All tools decorated with `@traceable` from `langsmith` for LangSmith trace visibility.

---

## 9. File Structure

```
automaton-auditor/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Model factory, env var loading
│   ├── state.py                     # AgentState, Evidence, JudicialOpinion
│   ├── graph.py                     # StateGraph definition, build + run
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── detectives.py            # context_builder, 3 detectives, aggregator
│   │   ├── judges.py                # make_judge_node factory, 3 personas
│   │   └── justice.py               # chief_justice, synthesis rules, report gen
│   └── tools/
│       ├── __init__.py
│       ├── git_tools.py             # safe_clone, extract_git_history
│       ├── ast_tools.py             # All AST check functions
│       └── pdf_tools.py             # ingest_pdf, search_keywords, extract_images
├── rubric/
│   └── week2_rubric.json            # Machine-readable constitution
├── audit/
│   ├── report_bypeer_received/      # Reports peer generated about YOUR code
│   ├── report_onpeer_generated/     # Reports YOUR agent generated about peer's code
│   ├── report_onself_generated/     # Reports YOUR agent generated about YOUR OWN code
│   └── langsmith_logs/              # Trace exports
├── .env                             # API keys — in .gitignore
├── .gitignore
├── pyproject.toml                   # uv project config
├── README.md                        # Run instructions
└── Dockerfile                       # Optional
```

---

## 10. Output Specification

### 10.1 Report Header

```markdown
# Automaton Auditor — Final Verdict

## Audit Metadata
| Field | Value |
|-------|-------|
| Repository | {repo_url} |
| Git Commit | {git_commit_hash} |
| PDF Report | {pdf_path} |
| Audit Date | {timestamp} |
| Detective Model | {model_metadata["layer1"]} |
| Judge Model | {model_metadata["layer2"]} |
| Synthesis | deterministic |
```

### 10.2 Per-Criterion Section

Each of the 4 rubric dimensions produces:

```markdown
## {criterion_name} — Score: {final_score}/5

### Judicial Opinions
- **Prosecutor** (Score: {p_score}): {p_argument}
- **Defense** (Score: {d_score}): {d_argument}
- **Tech Lead** (Score: {t_score}): {t_argument}

### Resolution
**Rule Applied:** {rule_name}
**Rationale:** {why_this_rule_fired}

### Dissent
{summary_of_losing_argument}
```

### 10.3 Remediation Plan

```markdown
## Remediation Plan

### High Priority
1. **{criterion_id}** — File: `{path}` — {issue_description}
   Fix: {specific_instruction}

### Medium Priority
...
```

---

## 11. Observability

### LangSmith Integration

Automatic via environment variables:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=automaton-auditor
```

Custom tool traces via `@traceable` decorator on all functions in `src/tools/`.

### Expected Trace Tree

```
▼ run_audit
  ▼ context_builder                          [node]
  ▼ repo_detective                           [node]  ── parallel
    ├── SafeGitClone                         [tool]
    ├── ExtractGitHistory                    [tool]
    ├── ASTCheckStateGraph                   [tool]
    ├── ASTCheckPydanticModels               [tool]
    ├── ASTCheckParallelEdges                [tool]
    ├── ASTCheckSandboxing                   [tool]
    └── ASTCheckStructuredOutput             [tool]
  ▼ doc_detective                            [node]  ── parallel
    ├── IngestPDF                            [tool]
    └── SearchKeywords                       [tool]
  ▼ vision_detective                         [node]  ── parallel
    └── ExtractImages                        [tool]
  ▼ evidence_aggregator                      [node]
  ▼ prosecutor                              [node]  ── parallel
    └── ChatOpenAI (×N criteria)             [llm]
  ▼ defense                                 [node]  ── parallel
    └── ChatOpenAI (×N criteria)             [llm]
  ▼ tech_lead                               [node]  ── parallel
    └── ChatOpenAI (×N criteria)             [llm]
  ▼ chief_justice                           [node]
```

---

## 12. Constraints & Non-Goals

### Constraints
- Must use LangGraph `StateGraph` (not CrewAI, AutoGen, etc.)
- Must use Pydantic models for Evidence and JudicialOpinion
- Must use AST parsing for code analysis (not regex)
- Must use `tempfile` for sandboxed cloning
- Must trace with LangSmith
- Must use `uv` as package manager
- Self-audit (`report_onself_generated`) is a required deliverable

### Non-Goals
- Real-time streaming UI
- Persistent database storage
- Human-in-the-loop during audit (post-audit feedback is separate)
- Multi-language repo analysis (Python only)

---

## 13. Architectural Decisions Log

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | Hierarchical fan-out/fan-in over peer-to-peer | Fixed workflow, no dynamic routing needed. Simpler to debug and trace. |
| ADR-002 | Shared TypedDict state over message passing | Structured data models, not chat messages. Native LangGraph pattern. |
| ADR-003 | Sync node (evidence_aggregator) between layers | Cross-referencing requires all evidence before judges run. |
| ADR-004 | List-style join edges | Prevents destination node executing multiple times per fan-in. |
| ADR-005 | Fact-only Evidence model (no scores) | Prevents opinion contamination in evidence pool. |
| ADR-006 | AST over regex for code analysis | Structural understanding. Rubric penalizes regex (Score 3 vs Score 5). |
| ADR-007 | Rubric loaded once, distributed via state | Single source of truth. Role-appropriate filtering by target_artifact. |
| ADR-008 | Forensic protocols mapped per dimension | Traceable chain: rubric → criterion → goals → evidence. |
| ADR-009 | Judge factory with shared base + persona overlay | DRY principle. Instructor confirmed this pattern. |
| ADR-010 | Integer 1–5 scale with rubric anchors | Research-backed (G-Eval). More reliable than 1–10 or binary. |
| ADR-011 | Deterministic conditional triggers for synthesis | Reproducible, auditable. Rubric awards Score 5 for deterministic rules. |
| ADR-012 | Dissent in every criterion | Makes report actionable. Required by rubric synthesis_rules. |
| ADR-013 | Single debate round (multi-round ready) | MVP simplicity. Architecture supports conditional edge for rounds. |
| ADR-014 | Per-layer model config via env vars | Cost optimization. Instructor recommended. Enables LiteLLM swap. |
| ADR-015 | Git commit hash + model name in report | Reproducibility. Instructor explicitly required. |