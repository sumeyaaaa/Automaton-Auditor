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
   - Copy `.env.example` to `.env` and fill in your API keys
   - Required: `DEEPSEEK_API_KEY` (default provider)
   - Optional: `OPENAI_API_KEY`, `XAI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`
   - Optional: `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` for observability

## Usage

### Running an Interim Audit (Detectives Only)

For interim submission, run the detective graph (without judges):

```bash
python -m src.graph <repo_url> <pdf_path> --interim
```

Example:
```bash
# Supports both PDF and Markdown reports
python -m src.graph https://github.com/user/repo.git reports/submission.pdf --interim
python -m src.graph https://github.com/user/repo.git reports/interim_report.md --interim
```

This will:
1. Run all three detectives in parallel (RepoInvestigator, DocAnalyst, VisionInspector)
2. Aggregate evidence
3. Save evidence to `audit/report_generated/{owner}/{repo_name}/interim_evidence.json` (automatically organized by repository)

### Running a Complete Audit (Final Submission)

Run the full auditor with judges and Chief Justice:

```bash
python -m src.graph <repo_url> <pdf_path>
```

Example:
```bash
# Supports both PDF and Markdown reports
python -m src.graph https://github.com/user/repo.git reports/submission.pdf
python -m src.graph https://github.com/user/repo.git reports/interim_report.md
```

This will:
1. Run the complete audit pipeline (detectives → judges → synthesis)
2. Save the audit report to `audit/report_generated/{owner}/{repo_name}/audit_report.md`
3. Save evidence to `audit/report_generated/{owner}/{repo_name}/interim_evidence.json` (automatically)

### Programmatic Usage

#### Interim Audit (Detectives Only)
```python
from pathlib import Path
from src.graph import run_interim_audit

# Run interim audit (detectives only)
# output_path is optional - will auto-generate repo-specific path if None
final_state = run_interim_audit(
    repo_url="https://github.com/user/repo.git",
    pdf_path="reports/submission.pdf",
    rubric_path="rubric.json",
    output_path=None  # Auto: audit/report_generated/{owner}/{repo_name}/interim_evidence.json
)

# Access collected evidence
evidences = final_state["evidences"]
print(f"Collected evidence from {len(evidences)} sources")
```

#### Complete Audit
```python
from pathlib import Path
from src.graph import run_audit

# Run complete audit
# output_path is optional - will auto-generate repo-specific path if using default
final_state = run_audit(
    repo_url="https://github.com/user/repo.git",
    pdf_path="reports/submission.pdf",
    rubric_path="rubric.json",
    output_path=None  # Auto: audit/report_generated/{owner}/{repo_name}/audit_report.md
)

# Access final report
report = final_state["final_report"]
print(f"Overall Score: {report.overall_score}/5.0")

# Both audit_report.md and interim_evidence.json are saved in the same folder
```

## Project Structure

```
Automaton-Auditor/
├── src/
│   ├── state.py              # Pydantic models and TypedDict state definitions
│   ├── graph.py              # Main LangGraph orchestration
│   ├── config.py             # Model factory and environment configuration
│   ├── exceptions.py         # Custom exception classes
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
├── audit/
│   ├── report_generated/           # Auto-organized by repository
│   │   ├── {owner}/
│   │   │   └── {repo_name}/
│   │   │       ├── audit_report.md      # Full audit report
│   │   │       └── interim_evidence.json # Evidence collected
│   ├── report_onself_generated/    # Self-audit reports (symlinked/copied)
│   ├── report_onpeer_generated/    # Peer audit reports (symlinked/copied)
│   └── report_bypeer_received/     # Reports received from peers
├── reports/
│   └── final_report.pdf            # Final PDF report for submission
├── rubric.json               # Machine-readable evaluation rubric
├── pyproject.toml            # Project dependencies (uv)
├── Dockerfile                # Containerized runtime (optional)
├── .env.example              # Environment variables template
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

### File Organization

Reports and evidence are automatically organized by repository:

```
audit/report_generated/
├── {owner}/
│   └── {repo_name}/
│       ├── audit_report.md          # Full audit report with scores
│       └── interim_evidence.json    # Raw evidence collected by detectives
```

**Example:**
- Repository: `https://github.com/sumeyaaaa/Automaton-Auditor`
- Report: `audit/report_generated/sumeyaaaa/Automaton-Auditor/audit_report.md`
- Evidence: `audit/report_generated/sumeyaaaa/Automaton-Auditor/interim_evidence.json`

This ensures:
- Multiple repositories can be audited without overwriting each other
- Each repository's audit history is preserved
- Easy navigation and comparison between different audits

## Docker Deployment (Optional)

Build and run using Docker:

```bash
# Build the image
docker build -t automaton-auditor .

# Run an audit
docker run --env-file .env automaton-auditor \
  python -m src.graph <repo_url> <pdf_path>
```

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

## Final Submission Structure

This repository is structured according to the Week 2 requirements:

- **Source Code**: All required modules in `src/`
- **Infrastructure**: `pyproject.toml`, `.env.example`, `Dockerfile`
- **Audit Reports**: 
  - `audit/report_generated/{owner}/{repo}/` - Auto-organized by repository (both `audit_report.md` and `interim_evidence.json`)
  - `audit/report_onself_generated/` - Self-audit report (convenience copy)
  - `audit/report_onpeer_generated/` - Peer audit report (convenience copy)
  - `audit/report_bypeer_received/` - Report received from peer
- **Documentation**: `README.md`, `doc.md`, `reports/final_report.pdf`

## License

[Specify your license here]

## Acknowledgments

Built for the FDE Challenge Week 2: The Automaton Auditor 
