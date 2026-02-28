"""
Chief Justice node for synthesizing final verdict.
Implements deterministic conflict resolution rules.
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from src.state import AgentState, AuditReport, CriterionResult, JudicialOpinion

logger = logging.getLogger(__name__)


def chief_justice_node(state: AgentState) -> AgentState:
    """Chief Justice: The Synthesis Engine.
    
    Resolves dialectical conflict using hardcoded deterministic rules.
    Generates final audit report and persists it to disk.
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
    
    # Serialize to Markdown
    markdown_report = final_report.to_markdown()
    
    # Persist report to disk (production-ready: node handles its own I/O)
    _persist_report_to_disk(markdown_report, repo_url, git_commit_hash)
    
    # Return Markdown string (required by AgentState.final_report: str)
    return {
        "final_report": markdown_report,
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
    1. Security Override: Actual security violations cap score at 3
       (triggered by low prosecutor score + violation phrases, NOT by
       mere mention of security-related words in praise)
    2. Fact Supremacy: Evidence overrules opinion
    3. Functionality Weight: Tech Lead carries weight for architecture
    4. Variance Re-evaluation: High variance triggers re-evaluation
    """
    scores = [s for s in [prosecutor_score, defense_score, tech_lead_score] if s is not None]
    
    if not scores:
        return 1
    
    # Rule 1: Security Override
    # Only cap the score when the Prosecutor ACTUALLY found security problems
    # (indicated by a low prosecutor score), not just because they mentioned
    # security-related words in their argument (which could be praise).
    prosecutor_opinion = next(
        (op for op in opinions if op.judge == "Prosecutor"), None
    )
    if prosecutor_score is not None and prosecutor_score <= 2:
        prosecutor_arg = prosecutor_opinion.argument.lower() if prosecutor_opinion else ""
        security_violation_phrases = [
            "os.system() call",
            "os.system() detected",
            "eval() call",
            "exec() call",
            "injection risk",
            "unsanitized input",
            "arbitrary command",
            "catastrophic security",
            "fundamentally unsafe",
        ]
        if any(phrase in prosecutor_arg for phrase in security_violation_phrases):
            if "safe_tool_engineering" in dimension_id:
                return min(3, max(scores))  # Cap at 3 only for actual violations
    
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


def _extract_relative_path(location: str) -> Optional[tuple[str, Optional[str]]]:
    """Extract relative file path and optional line number from evidence location.
    
    Handles:
    - Windows temp paths: "C:\\Users\\...\\auditor_repo_xxx\\repo\\src\\file.py" -> "src/file.py"
    - Unix paths: "/tmp/auditor_repo_xxx/repo/src/file.py" -> "src/file.py"
    - Relative paths: "src/file.py:42" -> ("src/file.py", "42")
    - URLs: "https://..." -> None
    
    Returns:
        Tuple of (relative_path, line_number) or None if not a file path
    """
    if not location or location.startswith("http") or location.startswith("cross_ref"):
        return None
    
    # Handle Windows temp directory pattern
    # Match: C:\Users\...\auditor_repo_xxx\repo\src\file.py or similar
    temp_pattern = r".*[\\/]auditor_repo_[^\\/]+[\\/]repo[\\/](.+)"
    match = re.search(temp_pattern, location.replace("\\", "/"))
    if match:
        path_str = match.group(1).replace("\\", "/")
    else:
        # Try to extract relative path directly
        # Check if it looks like a file path (contains .py, .js, etc.)
        if "." in location and not location.startswith("C:"):
            path_str = location.replace("\\", "/")
        else:
            return None
    
    # Extract line number if present (format: "path:line" or "path:line:col")
    if ":" in path_str:
        parts = path_str.rsplit(":", 1)
        file_path = parts[0]
        line_num = parts[1] if parts[1].isdigit() else None
    else:
        file_path = path_str
        line_num = None
    
    # Only return if it looks like a source file path
    if "/" in file_path or file_path.endswith((".py", ".js", ".ts", ".md", ".json", ".yaml", ".yml")):
        return (file_path, line_num)
    
    return None


def _extract_complete_sentences(text: str, max_sentences: int = 2) -> str:
    """Extract complete sentences from text without truncation.
    
    Args:
        text: Input text
        max_sentences: Maximum number of sentences to extract
        
    Returns:
        Complete sentences (up to max_sentences)
    """
    if not text:
        return ""
    
    # Split by sentence endings, but preserve them
    sentences = re.split(r'([.!?]\s+)', text)
    result = []
    char_count = 0
    
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            sentence = sentences[i] + sentences[i + 1]
        else:
            sentence = sentences[i]
        
        if len(result) >= max_sentences:
            break
        
        # Limit total length to ~300 chars
        if char_count + len(sentence) > 300 and result:
            break
        
        result.append(sentence.strip())
        char_count += len(sentence)
    
    if not result:
        # Fallback: first 200 chars if no sentence breaks found
        return text[:200].strip()
    
    return " ".join(result)


def _generate_remediation(
    dimension_id: str,
    dimension_name: str,
    final_score: int,
    opinions: List[JudicialOpinion],
) -> str:
    """Generate specific, file-level remediation instructions."""
    if final_score >= 4:
        return f"{dimension_name} meets requirements. Minor improvements may be possible."
    
    prosecutor = next((op for op in opinions if op.judge == "Prosecutor"), None)
    tech_lead = next((op for op in opinions if op.judge == "TechLead"), None)
    
    remediation_parts = [f"To improve {dimension_name}:"]
    
    # Extract file-specific issues from cited evidence (deduplicated)
    file_issues: Dict[str, List[str]] = {}
    seen_issues = set()  # For deduplication
    
    if prosecutor and prosecutor.cited_evidence:
        for location in prosecutor.cited_evidence:
            path_info = _extract_relative_path(location)
            if path_info:
                file_path, line_num = path_info
                
                # Create unique key for deduplication
                issue_key = f"{file_path}:{line_num or 'no-line'}"
                if issue_key in seen_issues:
                    continue
                seen_issues.add(issue_key)
                
                if file_path not in file_issues:
                    file_issues[file_path] = []
                
                # Extract complete sentence from prosecutor argument
                issue_summary = _extract_complete_sentences(prosecutor.argument, max_sentences=1)
                if not issue_summary:
                    issue_summary = "Issue identified by Prosecutor"
                
                # Format with line number if available
                if line_num:
                    file_issues[file_path].append(f"Line {line_num}: {issue_summary}")
                else:
                    file_issues[file_path].append(issue_summary)
    
    # Add file-specific remediation (deduplicated)
    for file_path, issues in sorted(file_issues.items()):
        for issue in issues:
            remediation_parts.append(f"- Fix {file_path} - {issue}")
    
    # Add general issues from prosecutor if no file-specific ones found
    if not file_issues and prosecutor:
        arg = prosecutor.argument.lower()
        if "security" in arg:
            remediation_parts.append(
                "- Implement proper security sandboxing for all system operations"
            )
        if "missing" in arg or "absent" in arg:
            # Extract complete sentence
            issue_text = _extract_complete_sentences(prosecutor.argument, max_sentences=1)
            if issue_text:
                remediation_parts.append(f"- Address missing elements: {issue_text}")
    
    # Add technical guidance from tech lead (complete sentences, not truncated)
    if tech_lead:
        tech_guidance = _extract_complete_sentences(tech_lead.argument, max_sentences=1)
        if tech_guidance:
            remediation_parts.append(f"- Technical guidance: {tech_guidance}")
    
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


def _parse_repo_owner_and_name(repo_url: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a GitHub-style repo URL into (owner, repo_name).
    
    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    
    Returns:
        (owner, repo) or (None, None) if parsing fails.
    """
    url = repo_url.strip()
    
    # SSH form: git@github.com:owner/repo.git
    if url.startswith("git@"):
        try:
            _, rest = url.split(":", 1)
            rest = rest.rstrip("/")
            if rest.endswith(".git"):
                rest = rest[:-4]
            parts = rest.split("/")
            if len(parts) >= 2:
                return parts[-2], parts[-1]
        except ValueError:
            return None, None
        return None, None
    
    # HTTPS form: https://github.com/owner/repo(.git)
    if url.startswith("http"):
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
    
    return None, None


def _persist_report_to_disk(markdown_report: str, repo_url: str, git_commit_hash: str) -> None:
    """Persist the final audit report to disk in repo-specific folder.
    
    This makes the Chief Justice node production-ready by handling its own I/O,
    ensuring the report is always saved even if the runner function fails.
    
    Args:
        markdown_report: The complete Markdown report string
        repo_url: Repository URL for folder organization
        git_commit_hash: Git commit hash for metadata
    """
    try:
        # Derive repo-specific output path
        owner, name = _parse_repo_owner_and_name(repo_url)
        if owner and name:
            output_path = (
                Path("audit") / "report_generated" / owner / name / "audit_report.md"
            )
        else:
            # Fallback: safe slug from the URL itself
            safe_slug = (
                repo_url.replace("://", "_")
                .replace("/", "_")
                .replace(":", "_")
                .replace("\\", "_")
            )
            output_path = (
                Path("audit") / "report_generated" / safe_slug / "audit_report.md"
            )
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write report to disk
        output_path.write_text(markdown_report, encoding="utf-8")
        logger.info(f"Chief Justice: Report persisted to {output_path}")
        
    except Exception as e:
        # Log error but don't fail the node - report is still in state
        logger.error(f"Chief Justice: Failed to persist report to disk: {e}")
        # Report remains in state["final_report"] so runner can still save it