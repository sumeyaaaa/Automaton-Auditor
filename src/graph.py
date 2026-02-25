"""
Main LangGraph orchestration for the Automaton Auditor.
Implements parallel fan-out/fan-in architecture for Detectives and Judges.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.config import get_model_metadata
from src.nodes.detectives import (
    doc_analyst_node,
    evidence_aggregator_node,
    repo_investigator_node,
    vision_inspector_node,
)
from src.state import AgentState


def load_rubric(rubric_path: Path) -> dict:
    """Load rubric JSON file."""
    with open(rubric_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_interim_graph(rubric_path: Path = Path("rubric.json")) -> StateGraph:
    """Create the partial auditor StateGraph for interim submission.
    
    Architecture (Interim):
    START -> [3 Detectives in parallel] -> EvidenceAggregator -> END
    
    Judges and Chief Justice are not included in interim submission.
    """
    # Load rubric
    rubric = load_rubric(rubric_path)
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes - Detective Layer only
    workflow.add_node("repo_investigator", repo_investigator_node)
    workflow.add_node("doc_analyst", doc_analyst_node)
    workflow.add_node("vision_inspector", vision_inspector_node)
    
    # Evidence Aggregation (Fan-In)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    
    # Define edges - Partial graph for interim
    # Start: Fan-out to Detectives
    workflow.add_edge(START, "repo_investigator")
    workflow.add_edge(START, "doc_analyst")
    workflow.add_edge(START, "vision_inspector")
    
    # Detectives -> Evidence Aggregator (Fan-In using list syntax)
    workflow.add_edge(
        ["repo_investigator", "doc_analyst", "vision_inspector"],
        "evidence_aggregator"
    )
    
    # Evidence Aggregator -> END
    workflow.add_edge("evidence_aggregator", END)
    
    # Compile graph
    return workflow.compile()


def create_auditor_graph(rubric_path: Path = Path("rubric.json")) -> StateGraph:
    """Create the complete auditor StateGraph.
    
    Architecture (Final):
    START -> [Detectives in parallel] -> EvidenceAggregator -> 
    [Judges in parallel] -> ChiefJustice -> END
    """
    # Import judges and justice for final graph
    from src.nodes.judges import defense_node, prosecutor_node, tech_lead_node
    from src.nodes.justice import chief_justice_node
    
    # Load rubric
    rubric = load_rubric(rubric_path)
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    # Detective Layer (Parallel Fan-Out)
    workflow.add_node("repo_investigator", repo_investigator_node)
    workflow.add_node("doc_analyst", doc_analyst_node)
    workflow.add_node("vision_inspector", vision_inspector_node)
    
    # Evidence Aggregation (Fan-In)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    
    # Judicial Layer (Parallel Fan-Out)
    workflow.add_node("prosecutor", prosecutor_node)
    workflow.add_node("defense", defense_node)
    workflow.add_node("tech_lead", tech_lead_node)
    
    # Supreme Court (Final Synthesis)
    workflow.add_node("chief_justice", chief_justice_node)
    
    # Define edges
    # Start: Fan-out to Detectives
    workflow.add_edge(START, "repo_investigator")
    workflow.add_edge(START, "doc_analyst")
    workflow.add_edge(START, "vision_inspector")
    
    # Detectives -> Evidence Aggregator (Fan-In using list syntax)
    workflow.add_edge(
        ["repo_investigator", "doc_analyst", "vision_inspector"],
        "evidence_aggregator"
    )
    
    # Evidence Aggregator -> Judges (Fan-Out)
    workflow.add_edge("evidence_aggregator", "prosecutor")
    workflow.add_edge("evidence_aggregator", "defense")
    workflow.add_edge("evidence_aggregator", "tech_lead")
    
    # Judges -> Chief Justice (Fan-In using list syntax)
    workflow.add_edge(
        ["prosecutor", "defense", "tech_lead"],
        "chief_justice"
    )
    
    # Chief Justice -> END
    workflow.add_edge("chief_justice", END)
    
    # Compile graph
    return workflow.compile()


def run_interim_audit(
    repo_url: str,
    pdf_path: str,
    rubric_path: Path = Path("rubric.json"),
    output_path: Path = Path("audit/interim_evidence.json"),
) -> dict:
    """Run the interim audit workflow (detectives only).
    
    Args:
        repo_url: GitHub repository URL to audit
        pdf_path: Path to PDF report
        rubric_path: Path to rubric JSON file
        output_path: Path to save the evidence output
        
    Returns:
        Final state with collected evidence
    """
    # Load rubric
    rubric = load_rubric(rubric_path)
    
    # Get model metadata for report
    model_metadata = get_model_metadata()
    
    # Initialize state
    initial_state: AgentState = {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": rubric["dimensions"],
        "evidences": {},
        "opinions": [],
        "final_report": None,
        "synthesis_rules": rubric.get("synthesis_rules", {}),
        "model_metadata": model_metadata,
        "git_commit_hash": "",  # Will be set by repo_investigator
    }
    
    # Create and run interim graph
    graph = create_interim_graph(rubric_path)
    final_state = graph.invoke(initial_state)
    
    # Save evidence to JSON
    if final_state.get("evidences"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_dict = {
            "repo_url": repo_url,
            "pdf_path": pdf_path,
            "git_commit_hash": final_state.get("git_commit_hash", ""),
            "evidences": {
                source: [
                    {
                        "criterion_id": ev.criterion_id,
                        "goal": ev.goal,
                        "found": ev.found,
                        "location": ev.location,
                        "confidence": ev.confidence,
                    }
                    for ev in evidence_list
                ]
                for source, evidence_list in final_state["evidences"].items()
            },
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evidence_dict, f, indent=2)
        print(f"Interim evidence saved to: {output_path}")
    
    return final_state


def run_audit(
    repo_url: str,
    pdf_path: str,
    rubric_path: Path = Path("rubric.json"),
    output_path: Path = Path("audit/report_generated/audit_report.md"),
) -> dict:
    """Run the complete audit workflow.
    
    Args:
        repo_url: GitHub repository URL to audit
        pdf_path: Path to PDF report
        rubric_path: Path to rubric JSON file
        output_path: Path to save the audit report
        
    Returns:
        Final state with audit report
    """
    # Import for final graph
    from src.nodes.judges import defense_node, prosecutor_node, tech_lead_node
    from src.nodes.justice import chief_justice_node
    
    # Load rubric
    rubric = load_rubric(rubric_path)
    
    # Get model metadata for report
    model_metadata = get_model_metadata()
    
    # Initialize state
    initial_state: AgentState = {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": rubric["dimensions"],
        "evidences": {},
        "opinions": [],
        "final_report": None,
        "synthesis_rules": rubric.get("synthesis_rules", {}),
        "model_metadata": model_metadata,
        "git_commit_hash": "",  # Will be set by repo_investigator
    }
    
    # Create and run graph
    graph = create_auditor_graph(rubric_path)
    final_state = graph.invoke(initial_state)
    
    # Save report to markdown
    if final_state.get("final_report"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_markdown = _serialize_report_to_markdown(final_state["final_report"])
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)
        print(f"Audit report saved to: {output_path}")
    
    return final_state


def _serialize_report_to_markdown(report) -> str:
    """Serialize AuditReport to Markdown format."""
    md_parts = [
        report.executive_summary,
        "",
        "# Criterion Breakdown",
        "",
    ]
    
    for criterion in report.criteria:
        md_parts.append(f"## {criterion.dimension_name}")
        md_parts.append(f"**Final Score:** {criterion.final_score}/5")
        md_parts.append("")
        
        # Judge opinions
        md_parts.append("### Judicial Opinions")
        for opinion in criterion.judge_opinions:
            md_parts.append(f"**{opinion.judge}** (Score: {opinion.score}/5)")
            md_parts.append(f"{opinion.argument}")
            if opinion.cited_evidence:
                md_parts.append(f"*Cited Evidence:* {', '.join(opinion.cited_evidence)}")
            md_parts.append("")
        
        # Dissent summary
        if criterion.dissent_summary:
            md_parts.append("### Dissent Summary")
            md_parts.append(criterion.dissent_summary)
            md_parts.append("")
        
        # Remediation
        md_parts.append("### Remediation")
        md_parts.append(criterion.remediation)
        md_parts.append("")
        md_parts.append("---")
        md_parts.append("")
    
    md_parts.append("# Comprehensive Remediation Plan")
    md_parts.append("")
    md_parts.append(report.remediation_plan)
    
    return "\n".join(md_parts)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m src.graph <repo_url> <pdf_path> [--interim]")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    pdf_path = sys.argv[2]
    is_interim = "--interim" in sys.argv
    
    if is_interim:
        run_interim_audit(repo_url, pdf_path)
    else:
        run_audit(repo_url, pdf_path)
