"""
Chief Justice node for synthesizing final verdict.
Implements deterministic conflict resolution rules.
"""
from datetime import datetime
from typing import Dict, List, Optional

from src.state import AgentState, AuditReport, CriterionResult, JudicialOpinion


def chief_justice_node(state: AgentState) -> AgentState:
    """Chief Justice: The Synthesis Engine.
    
    Resolves dialectical conflict using hardcoded deterministic rules.
    Generates final audit report.
    """
    opinions = state.get("opinions", [])
    repo_url = state["repo_url"]
    rubric_dimensions = state["rubric_dimensions"]
    synthesis_rules = state.get("synthesis_rules", {})
    
    # Group opinions by criterion
    opinions_by_criterion: Dict[str, List[JudicialOpinion]] = {}
    for opinion in opinions:
        criterion_id = opinion.criterion_id
        if criterion_id not in opinions_by_criterion:
            opinions_by_criterion[criterion_id] = []
        opinions_by_criterion[criterion_id].append(opinion)
    
    # Process each criterion
    criterion_results = []
    total_score = 0.0
    
    for dimension in rubric_dimensions:
        dimension_id = dimension["id"]
        dimension_name = dimension["name"]
        
        # Get opinions for this criterion
        criterion_opinions = opinions_by_criterion.get(dimension_id, [])
        
        if not criterion_opinions:
            # No opinions - default low score
            result = CriterionResult(
                dimension_id=dimension_id,
                dimension_name=dimension_name,
                final_score=1,
                judge_opinions=[],
                dissent_summary="No judicial opinions were rendered for this criterion.",
                remediation=f"Implement {dimension_name} according to the rubric requirements.",
            )
            criterion_results.append(result)
            total_score += 1.0
            continue
        
        # Extract scores
        prosecutor_score = next(
            (op.score for op in criterion_opinions if op.judge == "Prosecutor"), None
        )
        defense_score = next(
            (op.score for op in criterion_opinions if op.judge == "Defense"), None
        )
        tech_lead_score = next(
            (op.score for op in criterion_opinions if op.judge == "TechLead"), None
        )
        
        scores = [s for s in [prosecutor_score, defense_score, tech_lead_score] if s is not None]
        
        if not scores:
            final_score = 1
        else:
            # Apply synthesis rules
            final_score = _synthesize_score(
                prosecutor_score,
                defense_score,
                tech_lead_score,
                criterion_opinions,
                synthesis_rules,
                dimension_id,
            )
        
        # Calculate variance
        if len(scores) >= 2:
            score_variance = max(scores) - min(scores)
        else:
            score_variance = 0
        
        # Generate dissent summary if variance > 2
        dissent_summary = None
        if score_variance > 2:
            dissent_summary = _generate_dissent_summary(criterion_opinions)
        
        # Generate remediation
        remediation = _generate_remediation(
            dimension_id, dimension_name, final_score, criterion_opinions
        )
        
        result = CriterionResult(
            dimension_id=dimension_id,
            dimension_name=dimension_name,
            final_score=final_score,
            judge_opinions=criterion_opinions,
            dissent_summary=dissent_summary,
            remediation=remediation,
        )
        
        criterion_results.append(result)
        total_score += final_score
    
    # Calculate overall score
    overall_score = total_score / len(rubric_dimensions) if rubric_dimensions else 1.0
    
    # Generate executive summary
    git_commit_hash = state.get("git_commit_hash", "")
    model_metadata = state.get("model_metadata", {})
    executive_summary = _generate_executive_summary(
        overall_score, criterion_results, repo_url, git_commit_hash, model_metadata
    )
    
    # Generate comprehensive remediation plan
    remediation_plan = _generate_comprehensive_remediation_plan(criterion_results)
    
    # Create final report
    final_report = AuditReport(
        repo_url=repo_url,
        executive_summary=executive_summary,
        overall_score=overall_score,
        criteria=criterion_results,
        remediation_plan=remediation_plan,
    )
    
    return {
        "final_report": final_report,
    }


def _synthesize_score(
    prosecutor_score: Optional[int],
    defense_score: Optional[int],
    tech_lead_score: Optional[int],
    opinions: List[JudicialOpinion],
    synthesis_rules: Dict,
    dimension_id: str,
) -> int:
    """Apply deterministic synthesis rules to resolve score conflicts.
    
    Rules:
    1. Security Override: Security flaws cap score at 3
    2. Fact Supremacy: Evidence overrules opinion
    3. Functionality Weight: Tech Lead carries weight for architecture
    4. Variance Re-evaluation: High variance triggers re-evaluation
    """
    scores = [s for s in [prosecutor_score, defense_score, tech_lead_score] if s is not None]
    
    if not scores:
        return 1
    
    # Rule 1: Security Override
    prosecutor_opinion = next(
        (op for op in opinions if op.judge == "Prosecutor"), None
    )
    if prosecutor_opinion:
        prosecutor_arg = prosecutor_opinion.argument.lower()
        security_keywords = [
            "security",
            "vulnerability",
            "sandbox",
            "os.system",
            "injection",
            "unsanitized",
        ]
        if any(keyword in prosecutor_arg for keyword in security_keywords):
            if "safe_tool_engineering" in dimension_id or "security" in prosecutor_arg:
                return min(3, max(scores))  # Cap at 3
    
    # Rule 2: Fact Supremacy (handled via evidence confidence in opinions)
    # If evidence confidence is low, prosecutor's low score is weighted higher
    
    # Rule 3: Functionality Weight
    if dimension_id == "graph_orchestration":
        if tech_lead_score is not None:
            # Tech Lead carries higher weight for architecture
            if tech_lead_score >= 4:
                return max(scores)
            elif tech_lead_score <= 2:
                return min(scores)
    
    # Rule 4: Variance Re-evaluation
    score_variance = max(scores) - min(scores)
    if score_variance > 2:
        # Re-evaluate: if Tech Lead is middle ground, use it
        if tech_lead_score is not None:
            if min(scores) < tech_lead_score < max(scores):
                return tech_lead_score
        # Otherwise, be conservative (lower score)
        return min(scores) + 1 if min(scores) < 3 else min(scores)
    
    # Default: Weighted average (Tech Lead 40%, Prosecutor 30%, Defense 30%)
    weighted_sum = 0.0
    weight_total = 0.0
    
    if tech_lead_score is not None:
        weighted_sum += tech_lead_score * 0.4
        weight_total += 0.4
    if prosecutor_score is not None:
        weighted_sum += prosecutor_score * 0.3
        weight_total += 0.3
    if defense_score is not None:
        weighted_sum += defense_score * 0.3
        weight_total += 0.3
    
    if weight_total > 0:
        final = round(weighted_sum / weight_total)
        return max(1, min(5, final))
    
    return round(sum(scores) / len(scores))


def _generate_dissent_summary(opinions: List[JudicialOpinion]) -> str:
    """Generate summary of judicial disagreement."""
    prosecutor = next((op for op in opinions if op.judge == "Prosecutor"), None)
    defense = next((op for op in opinions if op.judge == "Defense"), None)
    tech_lead = next((op for op in opinions if op.judge == "TechLead"), None)
    
    summary_parts = []
    
    if prosecutor and defense:
        if prosecutor.score != defense.score:
            summary_parts.append(
                f"The Prosecutor (score: {prosecutor.score}) argued: {prosecutor.argument[:200]}... "
                f"However, the Defense (score: {defense.score}) countered: {defense.argument[:200]}..."
            )
    
    if tech_lead:
        if prosecutor and tech_lead.score != prosecutor.score:
            summary_parts.append(
                f"The Tech Lead (score: {tech_lead.score}) provided a pragmatic assessment "
                f"focusing on: {tech_lead.argument[:200]}..."
            )
    
    return " ".join(summary_parts) if summary_parts else "No significant dissent among judges."


def _generate_remediation(
    dimension_id: str,
    dimension_name: str,
    final_score: int,
    opinions: List[JudicialOpinion],
) -> str:
    """Generate specific remediation instructions."""
    if final_score >= 4:
        return f"{dimension_name} meets requirements. Minor improvements may be possible."
    
    prosecutor = next((op for op in opinions if op.judge == "Prosecutor"), None)
    tech_lead = next((op for op in opinions if op.judge == "TechLead"), None)
    
    remediation_parts = [f"To improve {dimension_name}:"]
    
    if prosecutor:
        # Extract specific issues from prosecutor
        arg = prosecutor.argument.lower()
        if "missing" in arg or "absent" in arg:
            remediation_parts.append(
                f"- Address missing elements identified by the Prosecutor: {prosecutor.argument[:150]}"
            )
        if "security" in arg:
            remediation_parts.append(
                "- Implement proper security sandboxing for all system operations"
            )
    
    if tech_lead:
        remediation_parts.append(
            f"- Follow technical guidance: {tech_lead.argument[:150]}"
        )
    
    # Add dimension-specific remediation
    if dimension_id == "state_management_rigor":
        remediation_parts.append(
            "- Ensure state uses Pydantic BaseModel or TypedDict with Annotated reducers"
        )
    elif dimension_id == "graph_orchestration":
        remediation_parts.append(
            "- Implement parallel fan-out/fan-in patterns for Detectives and Judges"
        )
    elif dimension_id == "structured_output_enforcement":
        remediation_parts.append(
            "- Use .with_structured_output() or .bind_tools() for all Judge LLM calls"
        )
    
    return "\n".join(remediation_parts)


def _generate_executive_summary(
    overall_score: float,
    criterion_results: List[CriterionResult],
    repo_url: str,
    git_commit_hash: str = "",
    model_metadata: Optional[Dict] = None,
) -> str:
    """Generate executive summary of the audit."""
    summary_parts = [
        f"# Automaton Auditor — Final Verdict",
        f"",
        f"## Audit Metadata",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Repository | {repo_url} |",
        f"| Git Commit | {git_commit_hash or 'N/A'} |",
        f"| Audit Date | {datetime.now().isoformat()} |",
    ]
    
    if model_metadata:
        summary_parts.extend([
            f"| Detective Model | {model_metadata.get('layer1', {}).get('model', 'N/A')} |",
            f"| Judge Model | {model_metadata.get('layer2', {}).get('model', 'N/A')} |",
            f"| Synthesis | deterministic |",
        ])
    
    summary_parts.extend([
        f"",
        f"## Executive Summary",
        f"",
        f"**Overall Score:** {overall_score:.2f}/5.0",
        f"",
    ])
    
    # Count scores by range
    high_scores = sum(1 for cr in criterion_results if cr.final_score >= 4)
    medium_scores = sum(1 for cr in criterion_results if 2 <= cr.final_score < 4)
    low_scores = sum(1 for cr in criterion_results if cr.final_score < 2)
    
    summary_parts.append(
        f"**Score Distribution:** {high_scores} high (4-5), "
        f"{medium_scores} medium (2-3), {low_scores} low (1)"
    )
    summary_parts.append("")
    
    # Highlight critical issues
    critical_issues = [
        cr for cr in criterion_results
        if cr.final_score <= 2 and "security" in cr.dimension_name.lower()
    ]
    if critical_issues:
        summary_parts.append("**Critical Issues:**")
        for issue in critical_issues:
            summary_parts.append(f"- {issue.dimension_name}: Score {issue.final_score}")
        summary_parts.append("")
    
    # Highlight strengths
    strengths = [cr for cr in criterion_results if cr.final_score >= 4]
    if strengths:
        summary_parts.append("**Strengths:**")
        for strength in strengths[:3]:  # Top 3
            summary_parts.append(f"- {strength.dimension_name}: Score {strength.final_score}")
    
    return "\n".join(summary_parts)


def _generate_comprehensive_remediation_plan(
    criterion_results: List[CriterionResult],
) -> str:
    """Generate comprehensive remediation plan."""
    plan_parts = [
        "# Comprehensive Remediation Plan",
        "",
        "## Priority 1: Critical Issues (Score ≤ 2)",
    ]
    
    critical = [cr for cr in criterion_results if cr.final_score <= 2]
    for cr in critical:
        plan_parts.append(f"### {cr.dimension_name}")
        plan_parts.append(cr.remediation)
        plan_parts.append("")
    
    plan_parts.append("## Priority 2: Improvements (Score 2-3)")
    medium = [cr for cr in criterion_results if 2 < cr.final_score < 4]
    for cr in medium:
        plan_parts.append(f"### {cr.dimension_name}")
        plan_parts.append(cr.remediation)
        plan_parts.append("")
    
    plan_parts.append("## Priority 3: Enhancements (Score ≥ 4)")
    high = [cr for cr in criterion_results if cr.final_score >= 4]
    if high:
        plan_parts.append("These areas meet requirements but could be enhanced:")
        for cr in high:
            plan_parts.append(f"- {cr.dimension_name}: {cr.remediation}")
    
    return "\n".join(plan_parts)

