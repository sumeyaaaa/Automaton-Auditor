"""
Main LangGraph orchestration for the Automaton Auditor.

This is the brain wiring — it connects detectives, judges, and the
chief justice into a working multi-agent pipeline.

Two graphs are available:
- Interim: Detectives only (for testing evidence collection)
- Final: Full pipeline including judges and synthesis

Architecture spec reference: Section 5 — Graph Wiring
"""
import logging
logging.basicConfig(level=logging.INFO)
import json
from datetime import datetime
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from src.config import get_model_metadata
from src.exceptions import NodeExecutionError, RubricLoadError
from src.nodes.detectives import (
    doc_analyst_node,
    evidence_aggregator_node,
    repo_investigator_node,
    vision_inspector_node,
)
from src.state import AgentState


# ──────────────────────────────────────────────
# Rubric Loading
# ──────────────────────────────────────────────

def load_rubric(rubric_path: Path) -> dict:
    """Load and validate the rubric JSON file.

    The rubric is the 'constitution' of the courtroom — it defines
    what detectives look for and what judges score against.

    Args:
        rubric_path: Path to the rubric JSON file

    Returns:
        Parsed rubric dictionary with 'dimensions' and 'synthesis_rules'

    Raises:
        RubricLoadError: If file is missing, malformed, or invalid
    """
    if not rubric_path.exists():
        raise RubricLoadError(str(rubric_path), "Rubric file not found")

    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            rubric = json.load(f)

        if "dimensions" not in rubric:
            raise RubricLoadError(str(rubric_path), "Rubric missing 'dimensions' key")

        return rubric
    except json.JSONDecodeError as e:
        raise RubricLoadError(str(rubric_path), f"Invalid JSON: {e}")


# ──────────────────────────────────────────────
# Context Builder Node
#
# This node runs FIRST (Superstep 1). It loads the rubric
# and model metadata into state so every downstream node
# can access them without re-reading files.
# ──────────────────────────────────────────────

def context_builder_node(state: AgentState) -> dict:
    """Load rubric and model metadata into state.

    This is the initialization node. It reads the rubric JSON once
    and puts it into state where all detectives and judges can find it.
    It also records which AI models are being used for reproducibility.

    Runs at: Superstep 1 (before any detective)
    """
    rubric_path = Path(state.get("rubric_path", "rubric.json"))
    rubric = load_rubric(rubric_path)

    return {
        "rubric_dimensions": rubric["dimensions"],
        "synthesis_rules": rubric.get("synthesis_rules", {}),
        "model_metadata": get_model_metadata(),
    }


# ──────────────────────────────────────────────
# Graph Builders
# ──────────────────────────────────────────────

def create_interim_graph() -> StateGraph:
    """Build the interim graph — detectives only.

    This graph is for testing the evidence collection layer
    in isolation before wiring in judges.

    Architecture:
        START → context_builder
              → [3 detectives in PARALLEL]  (Superstep 2)
              → evidence_aggregator         (Superstep 3)
              → END
    """
    workflow = StateGraph(AgentState)

    # ── Nodes ──
    workflow.add_node("context_builder", context_builder_node)
    workflow.add_node("repo_investigator", repo_investigator_node)
    workflow.add_node("doc_analyst", doc_analyst_node)
    workflow.add_node("vision_inspector", vision_inspector_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)

    # ── Edges ──
    # Superstep 1: Initialize
    workflow.add_edge(START, "context_builder")

    # Superstep 2: Fan-out to 3 detectives in parallel
    workflow.add_edge("context_builder", "repo_investigator")
    workflow.add_edge("context_builder", "doc_analyst")
    workflow.add_edge("context_builder", "vision_inspector")

    # Superstep 3: Fan-in — all 3 must complete before aggregator runs
    # CRITICAL: Must use list syntax. Separate add_edge calls to the
    # same destination would cause it to run multiple times.
    workflow.add_edge(
        ["repo_investigator", "doc_analyst", "vision_inspector"],
        "evidence_aggregator",
    )

    # Superstep 4: End (no judges in interim)
    workflow.add_edge("evidence_aggregator", END)

    return workflow.compile()


def create_auditor_graph() -> StateGraph:
    """Build the complete auditor graph — detectives + judges + synthesis.

    Architecture:
        START → context_builder
              → [3 detectives in PARALLEL]     (Superstep 2)
              → evidence_aggregator            (Superstep 3)
              → [3 judges in PARALLEL]         (Superstep 4)
              → chief_justice                  (Superstep 5)
              → END
    """
    # Late import to avoid circular dependency and allow
    # interim graph to work without judge/justice modules
    from src.nodes.judges import defense_node, prosecutor_node, tech_lead_node
    from src.nodes.justice import chief_justice_node

    workflow = StateGraph(AgentState)

    # ── Nodes ──
    # Layer 0: Initialization
    workflow.add_node("context_builder", context_builder_node)

    # Layer 1: Detective Bureau (evidence collection)
    workflow.add_node("repo_investigator", repo_investigator_node)
    workflow.add_node("doc_analyst", doc_analyst_node)
    workflow.add_node("vision_inspector", vision_inspector_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)

    # Layer 2: Judicial Bench (scoring)
    workflow.add_node("prosecutor", prosecutor_node)
    workflow.add_node("defense", defense_node)
    workflow.add_node("tech_lead", tech_lead_node)

    # Layer 3: Supreme Court (synthesis)
    workflow.add_node("chief_justice", chief_justice_node)

    # ── Edges ──
    # Superstep 1: Initialize
    workflow.add_edge(START, "context_builder")

    # Superstep 2: Fan-out to 3 detectives in parallel
    workflow.add_edge("context_builder", "repo_investigator")
    workflow.add_edge("context_builder", "doc_analyst")
    workflow.add_edge("context_builder", "vision_inspector")

    # Superstep 3: Fan-in detectives → aggregator
    workflow.add_edge(
        ["repo_investigator", "doc_analyst", "vision_inspector"],
        "evidence_aggregator",
    )

    # Superstep 4: Fan-out to 3 judges in parallel
    workflow.add_edge("evidence_aggregator", "prosecutor")
    workflow.add_edge("evidence_aggregator", "defense")
    workflow.add_edge("evidence_aggregator", "tech_lead")

    # Superstep 5: Fan-in judges → chief justice
    workflow.add_edge(
        ["prosecutor", "defense", "tech_lead"],
        "chief_justice",
    )

    # Superstep 6: Done
    workflow.add_edge("chief_justice", END)

    return workflow.compile()


# ──────────────────────────────────────────────
# Runner Functions
# ──────────────────────────────────────────────

def run_interim_audit(
    repo_url: str,
    pdf_path: str,
    rubric_path: str = "rubric.json",
    output_path: Path = Path("audit/interim_evidence.json"),
) -> dict:
    """Run the interim audit — detectives only, no judges.

    Use this to test evidence collection in isolation.

    Args:
        repo_url: GitHub repository URL to audit
        pdf_path: Path to the PDF report
        rubric_path: Path to rubric JSON (passed to context_builder via state)
        output_path: Where to save the evidence JSON

    Returns:
        Final state dictionary with all collected evidence
    """
    # Initial state — only set what the graph needs to start.
    # context_builder will fill in rubric_dimensions and model_metadata.
    initial_state = {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_path": rubric_path,
        "git_commit_hash": "",
        "rubric_dimensions": [],
        "synthesis_rules": {},
        "model_metadata": {},
        "evidences": {},
        "opinions": [],
        "final_report": "",
    }

    try:
        graph = create_interim_graph()
        final_state = graph.invoke(initial_state)
    except Exception as e:
        raise NodeExecutionError(
            "interim_graph",
            f"Failed to execute interim audit: {e}",
        ) from e

    # Save evidence to JSON
    _save_evidence_json(final_state, output_path)

    return final_state


def run_audit(
    repo_url: str,
    pdf_path: str,
    rubric_path: str = "rubric.json",
    output_path: Path = Path("audit/report_generated/audit_report.md"),
) -> dict:
    """Run the complete audit — detectives + judges + synthesis.

    Args:
        repo_url: GitHub repository URL to audit
        pdf_path: Path to the PDF report
        rubric_path: Path to rubric JSON
        output_path: Where to save the final Markdown report

    Returns:
        Final state dictionary with audit report
    """
    initial_state = {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_path": rubric_path,
        "git_commit_hash": "",
        "rubric_dimensions": [],
        "synthesis_rules": {},
        "model_metadata": {},
        "evidences": {},
        "opinions": [],
        "final_report": "",
    }

    try:
        graph = create_auditor_graph()
        final_state = graph.invoke(initial_state)
    except Exception as e:
        raise NodeExecutionError(
            "full_graph",
            f"Failed to execute audit: {e}",
        ) from e

    # Save report
    report = final_state.get("final_report", "")
    if report:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Audit report saved to: {output_path}")

    return final_state


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _save_evidence_json(state: dict, output_path: Path) -> None:
    """Save collected evidence to a JSON file for inspection."""
    evidences = state.get("evidences", {})
    if not evidences:
        print("Warning: No evidence collected.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize Evidence objects to dicts
    evidence_dict = {
        "metadata": {
            "repo_url": state.get("repo_url", ""),
            "pdf_path": state.get("pdf_path", ""),
            "git_commit_hash": state.get("git_commit_hash", ""),
            "timestamp": datetime.now().isoformat(),
            "model_metadata": state.get("model_metadata", {}),
        },
        "evidences": {
            source: [
                {
                    "criterion_id": ev.criterion_id,
                    "goal": ev.goal,
                    "found": ev.found,
                    "location": ev.location,
                    "confidence": ev.confidence,
                    "rationale": ev.rationale,
                    # Save full content (up to 10000 chars as per Evidence model)
                    # Truncate only if absolutely necessary for JSON file size
                    "content": (ev.content[:10000] if ev.content else None),
                }
                for ev in ev_list
            ]
            for source, ev_list in evidences.items()
            if isinstance(ev_list, list)
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence_dict, f, indent=2, ensure_ascii=False)

    # Print summary (ASCII-only to avoid Windows encoding issues)
    total = sum(len(el) for el in evidences.values() if isinstance(el, list))
    print(f"Evidence saved: {total} items from {len(evidences)} sources -> {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m src.graph <repo_url> <pdf_path> [--interim]")
        sys.exit(1)

    repo_url = sys.argv[1]
    pdf_path = sys.argv[2]

    if "--interim" in sys.argv:
        run_interim_audit(repo_url, pdf_path)
    else:
        run_audit(repo_url, pdf_path)