# Automaton-Auditor
Orchestrating Deep LangGraph Swarms for Autonomous Governance - The Digital Courtroom

## Overview

The Automaton Auditor is a production-grade multi-agent system built with LangGraph that autonomously audits GitHub repositories and PDF reports. It implements a hierarchical "Digital Courtroom" architecture with:

- **Detective Layer**: Forensic agents that collect objective evidence
- **Judicial Layer**: Three distinct judge personas (Prosecutor, Defense, Tech Lead) that evaluate evidence
- **Supreme Court**: Chief Justice synthesizes final verdict using deterministic conflict resolution

## Architecture

```
START
  ├─> RepoInvestigator (Code Detective)
  ├─> DocAnalyst (Paperwork Detective)  } Parallel Fan-Out
  └─> VisionInspector (Diagram Detective)
         |
         v
  EvidenceAggregator (Fan-In)
         |
         v
  ├─> Prosecutor (Critical Lens)
  ├─> Defense (Optimistic Lens)        } Parallel Fan-Out
  └─> TechLead (Pragmatic Lens)
         |
         v
  ChiefJustice (Synthesis)
         |
         v
  END (Markdown Report)
```

## Installation

### Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`

### Setup

1. Clone the repository:
```bash
git clone <repo-url>
cd Automaton-Auditor
```

2. Install dependencies using `uv`:
```bash
uv sync
```

Or using `pip`:
```bash
pip install -e .
```

3. Configure environment variables:
   - Copy `.env.example` to `.env` (if not blocked by gitignore)
   - Set your API keys (at minimum, you need one LLM provider):
     - `DEEPSEEK_API_KEY`: For DeepSeek models (default, recommended for cost efficiency)
     - `OPENAI_API_KEY`: For OpenAI models (GPT-4o, optional)
     - `XAI_API_KEY`: For xAI/Grok models (optional)
     - `GROQ_API_KEY`: For Groq/Llama models (optional)
     - `GOOGLE_API_KEY`: For Google Gemini models (optional)
     - `LANGCHAIN_API_KEY`: For LangSmith tracing (optional but recommended)
     - `LANGCHAIN_TRACING_V2=true`: Enable tracing
     - `LANGCHAIN_PROJECT=automaton-auditor`: LangSmith project name

## Usage

### Running an Interim Audit (Detectives Only)

For interim submission, run the detective graph (without judges):

```bash
python -m src.graph <repo_url> <pdf_path> --interim
```

Example:
```bash
python -m src.graph https://github.com/user/repo.git reports/submission.pdf --interim
```

This will:
1. Run all three detectives in parallel (RepoInvestigator, DocAnalyst, VisionInspector)
2. Aggregate evidence
3. Save evidence to `audit/interim_evidence.json`

### Running a Complete Audit (Final Submission)

Run the full auditor with judges and Chief Justice:

```bash
python -m src.graph <repo_url> <pdf_path>
```

Example:
```bash
python -m src.graph https://github.com/user/repo.git reports/submission.pdf
```

### Programmatic Usage

#### Interim Audit (Detectives Only)
```python
from pathlib import Path
from src.graph import run_interim_audit

# Run interim audit (detectives only)
final_state = run_interim_audit(
    repo_url="https://github.com/user/repo.git",
    pdf_path="reports/submission.pdf",
    rubric_path=Path("rubric/week2_rubric.json"),
    output_path=Path("audit/interim_evidence.json")
)

# Access collected evidence
evidences = final_state["evidences"]
print(f"Collected evidence from {len(evidences)} sources")
```

#### Complete Audit
```python
from pathlib import Path
from src.graph import run_audit

# Run complete audit (self-audit by default)
final_state = run_audit(
    repo_url="https://github.com/user/repo.git",
    pdf_path="reports/submission.pdf",
    rubric_path=Path("rubric/week2_rubric.json"),
    audit_type="onself"  # Options: "onself", "onpeer", "bypeer"
)

# Access final report
report = final_state["final_report"]
print(f"Report length: {len(report)} characters")
# The report is a Markdown string saved to the audit directory
```

## Project Structure

```
Automaton-Auditor/
├── src/
│   ├── state.py              # Pydantic models and TypedDict state definitions
│   ├── graph.py              # Main LangGraph orchestration
│   ├── tools/
│   │   ├── git_tools.py     # Safe git cloning and history extraction
│   │   ├── ast_tools.py     # AST-based code structure analysis
│   │   ├── pdf_tools.py     # PDF parsing and document analysis
│   │   ├── repo_tools.py    # Wrapper combining git_tools + ast_tools
│   │   └── doc_tools.py     # Wrapper for pdf_tools (compatibility)
│   └── nodes/
│       ├── detectives.py    # RepoInvestigator, DocAnalyst, VisionInspector
│       ├── judges.py         # Prosecutor, Defense, TechLead
│       └── justice.py        # ChiefJustice synthesis engine
├── rubric/
│   └── week2_rubric.json     # Machine-readable evaluation rubric
├── audit/
│   ├── report_bypeer_received/      # Reports peer generated about YOUR code
│   ├── report_onpeer_generated/     # Reports YOUR agent generated about peer's code
│   ├── report_onself_generated/     # Reports YOUR agent generated about YOUR OWN code
│   └── langsmith_logs/              # Trace exports
├── pyproject.toml            # Project dependencies
├── README.md                 # This file
└── doc.md                    # Complete project specification
```

## Key Features

### 1. Forensic Evidence Collection
- **RepoInvestigator**: AST-based code analysis, git history extraction, security sandboxing
- **DocAnalyst**: PDF parsing with RAG-lite chunking, keyword search, cross-referencing
- **VisionInspector**: Image extraction and diagram analysis (optional)

### 2. Dialectical Judicial Process
- **Prosecutor**: Critical lens focusing on gaps and security flaws
- **Defense**: Optimistic lens rewarding effort and intent
- **Tech Lead**: Pragmatic lens evaluating functionality and maintainability

### 3. Deterministic Synthesis
- Hardcoded conflict resolution rules
- Security override (caps score at 3 for vulnerabilities)
- Fact supremacy (evidence overrules opinion)
- Variance re-evaluation for high-disagreement cases

### 4. Production-Grade Infrastructure
- Typed state with Pydantic models and reducers
- Parallel execution with proper fan-out/fan-in patterns
- Sandboxed tool execution
- Structured output enforcement
- LangSmith observability

## Rubric Dimensions

The auditor evaluates 10 dimensions:

1. **Git Forensic Analysis**: Commit history progression
2. **State Management Rigor**: Pydantic/TypedDict with reducers
3. **Graph Orchestration**: Parallel fan-out/fan-in patterns
4. **Safe Tool Engineering**: Sandboxed operations, security
5. **Structured Output Enforcement**: Pydantic validation for judges
6. **Judicial Nuance**: Distinct personas with dialectical synthesis
7. **Chief Justice Synthesis**: Deterministic conflict resolution
8. **Theoretical Depth**: Substantive explanations in PDF
9. **Report Accuracy**: Cross-reference file paths
10. **Swarm Visual**: Architectural diagram analysis

## Output

The auditor generates a structured Markdown report containing:

- **Executive Summary**: Overall score and key findings
- **Criterion Breakdown**: Detailed scores per dimension with:
  - Three judge opinions (Prosecutor, Defense, Tech Lead)
  - Dissent summaries (when variance > 2)
  - Specific remediation instructions
- **Comprehensive Remediation Plan**: Prioritized action items

Reports are saved to the appropriate directory based on audit type:
- Self-audit: `audit/report_onself_generated/{owner}/{repo}/audit_report.md`
- Peer audit: `audit/report_onpeer_generated/{owner}/{repo}/audit_report.md`
- Received peer audit: `audit/report_bypeer_received/{owner}/{repo}/audit_report.md`

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
black src/
ruff check src/
```

## License

[Specify your license here]

## Acknowledgments

Built for the FDE Challenge Week 2: The Automaton Auditor 
