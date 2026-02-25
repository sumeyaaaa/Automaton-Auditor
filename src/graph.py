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
from src.exceptions import NodeExecutionError, RubricLoadError
from src.nodes.detectives import (
    doc_analyst_node,
    evidence_aggregator_node,
    repo_investigator_node,
    vision_inspector_node,
)
from src.state import AgentState


def load_rubric(rubric_path: Path) -> dict:
    """Load rubric JSON file.
    
    Raises:
        RubricLoadError: If rubric file cannot be loaded
    """
    if not rubric_path.exists():
        raise RubricLoadError(str(rubric_path), "Rubric file not found")
    
    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            rubric = json.load(f)
        
        # Validate rubric structure
        if "dimensions" not in rubric:
            raise RubricLoadError(str(rubric_path), "Rubric missing 'dimensions' key")
        
        return rubric
    except json.JSONDecodeError as e:
        raise RubricLoadError(str(rubric_path), f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise RubricLoadError(str(rubric_path), f"Unexpected error: {str(e)}")


def should_continue_audit(state: AgentState) -> Literal["continue", "retry"]:
    """Conditional routing function for evidence aggregator.
    
    Determines if audit should continue based on evidence quality and completeness.
    Uses multiple heuristics to assess evidence quality before proceeding.
    
    Args:
        state: Current agent state
        
    Returns:
        "continue" to proceed to END or next layer, "retry" to retry evidence collection
    """
    evidences = state.get("evidences", {})
    
    # Check if we have evidence from at least one detective
    if not evidences:
        return "retry"
    
    # Count evidence sources and quality metrics
    evidence_sources = len(evidences)
    total_evidences = 0
    high_confidence_count = 0
    medium_confidence_count = 0
    low_confidence_count = 0
    
    for evidence_list in evidences.values():
        if isinstance(evidence_list, list):
            for evidence in evidence_list:
                total_evidences += 1
                if hasattr(evidence, "confidence"):
                    if evidence.confidence > 0.7:
                        high_confidence_count += 1
                    elif evidence.confidence > 0.4:
                        medium_confidence_count += 1
                    else:
                        low_confidence_count += 1
    
    # Require at least 2 evidence sources (repo, doc, or vision)
    if evidence_sources < 2:
        return "retry"
    
    # Require at least some high or medium confidence evidence
    if high_confidence_count == 0 and medium_confidence_count == 0:
        return "retry"
    
    # Require minimum total evidence count
    if total_evidences < 3:
        return "retry"
    
    # Check if we have evidence for critical dimensions
    rubric_dimensions = state.get("rubric_dimensions", [])
    if rubric_dimensions:
        # Count how many dimensions have evidence
        dimension_ids_with_evidence = set()
        for evidence_list in evidences.values():
            if isinstance(evidence_list, list):
                for evidence in evidence_list:
                    if hasattr(evidence, "criterion_id"):
                        dimension_ids_with_evidence.add(evidence.criterion_id)
        
        # Require evidence for at least 50% of dimensions
        if len(dimension_ids_with_evidence) < len(rubric_dimensions) * 0.5:
            return "retry"
    
    return "continue"


def validate_final_report(state: AgentState) -> Literal["complete", "incomplete"]:
    """Conditional routing function for chief justice.
    
    Validates that the final report is complete and meets quality standards before ending.
    Performs comprehensive validation of report structure and content quality.
    
    Args:
        state: Current agent state
        
    Returns:
        "complete" if report is valid and meets quality standards, "incomplete" to retry
    """
    final_report = state.get("final_report")
    
    if not final_report:
        return "incomplete"
    
    # Check if report has required fields with non-empty content
    if not hasattr(final_report, "executive_summary") or not final_report.executive_summary:
        return "incomplete"
    
    if len(final_report.executive_summary.strip()) < 100:
        return "incomplete"
    
    if not hasattr(final_report, "criteria") or not final_report.criteria:
        return "incomplete"
    
    if not hasattr(final_report, "remediation_plan") or not final_report.remediation_plan:
        return "incomplete"
    
    if len(final_report.remediation_plan.strip()) < 100:
        return "incomplete"
    
    # Check if all criteria have results
    rubric_dimensions = state.get("rubric_dimensions", [])
    if len(final_report.criteria) < len(rubric_dimensions):
        return "incomplete"
    
    # Validate each criterion has required fields
    for criterion in final_report.criteria:
        if not hasattr(criterion, "dimension_id") or not criterion.dimension_id:
            return "incomplete"
        if not hasattr(criterion, "final_score") or criterion.final_score < 1 or criterion.final_score > 5:
            return "incomplete"
        if not hasattr(criterion, "judge_opinions") or len(criterion.judge_opinions) != 3:
            return "incomplete"
        if not hasattr(criterion, "remediation") or len(criterion.remediation.strip()) < 50:
            return "incomplete"
    
    # Validate overall score is within valid range
    if final_report.overall_score < 1.0 or final_report.overall_score > 5.0:
        return "incomplete"
    
    # Check that all required judge personas are present
    for criterion in final_report.criteria:
        judges = {opinion.judge for opinion in criterion.judge_opinions}
        if judges != {"Prosecutor", "Defense", "TechLead"}:
            return "incomplete"
    
    return "complete"


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
    
    # Evidence Aggregator -> Conditional routing based on evidence quality
    workflow.add_conditional_edges(
        "evidence_aggregator",
        should_continue_audit,
        {
            "continue": END,  # For interim, we always end after evidence collection
            "retry": "repo_investigator",  # Retry if evidence quality is poor (future enhancement)
        }
    )

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

    # Chief Justice -> Conditional routing based on report completeness
    workflow.add_conditional_edges(
        "chief_justice",
        validate_final_report,
        {
            "complete": END,
            "incomplete": "chief_justice",  # Retry synthesis if incomplete
        }
    )

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
