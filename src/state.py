"""
State definitions for the Automaton Auditor.

This file defines the data contracts for the entire pipeline:
- Evidence: Facts collected by detectives (no opinions)
- JudicialOpinion: Scored opinions from judge personas
- CriterionResult: Synthesized result per rubric dimension
- AuditReport: Complete audit output (used internally by chief justice)
- AgentState: The shared TypedDict that flows through the graph

Every other module depends on these shapes. If a field name or type
changes here, it must change everywhere.

Architecture spec reference: Section 3 — State Schema
"""

import operator
import re
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import TypedDict


# ──────────────────────────────────────────────
# Detective Output
# ──────────────────────────────────────────────


class Evidence(BaseModel):
    """A single piece of forensic evidence collected by a Detective.

    Detectives collect FACTS only — no scores, no opinions, no recommendations.
    Each Evidence links to a rubric dimension via criterion_id so judges
    can filter relevant evidence when scoring.
    """

    criterion_id: str = Field(
        description="Which rubric dimension this evidence relates to",
        min_length=1,
        max_length=100,
    )
    goal: str = Field(
        description="What the detective was looking for",
        min_length=1,
        max_length=500,
    )
    found: bool = Field(
        description="Whether the artifact was present or absent (binary fact)"
    )
    content: Optional[str] = Field(
        default=None,
        description="Code snippet, commit log, or PDF excerpt",
        max_length=10000,
    )
    location: str = Field(
        description="File path:line, commit hash, or 'not_found'",
        min_length=1,
        max_length=500,
    )
    rationale: str = Field(
        description="Why the detective is confident in this finding",
        min_length=1,
        max_length=2000,
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0",
    )

    @field_validator("criterion_id")
    @classmethod
    def validate_criterion_id(cls, v: str) -> str:
        """Criterion IDs must be lowercase with underscores (e.g., 'git_forensic_analysis')."""
        v = v.strip()
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(
                f"criterion_id must be lowercase letters, numbers, underscores. Got: '{v}'"
            )
        return v


# ──────────────────────────────────────────────
# Judge Output
# ──────────────────────────────────────────────


class JudicialOpinion(BaseModel):
    """A scored opinion from a judge persona on a specific criterion.

    Each judge evaluates every rubric dimension independently.
    The score is 1-5 based on rubric anchors, and the argument
    must cite specific evidence to justify the score.

    Enforced via .with_structured_output(JudicialOpinion) in judges.py.
    """

    judge: Literal["Prosecutor", "Defense", "TechLead"] = Field(
        description="Which judge persona produced this opinion"
    )
    criterion_id: str = Field(
        description="Which rubric dimension is being scored",
        min_length=1,
        max_length=100,
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Score from 1 (Vibe Coder) to 5 (Master Thinker)",
    )
    argument: str = Field(
        description="Reasoning for this score, citing specific evidence (file paths, line numbers, code snippets)",
        min_length=20,
        max_length=2000,
    )
    cited_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence locations referenced in the argument",
    )

    @field_validator("criterion_id")
    @classmethod
    def validate_criterion_id(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError(
                f"criterion_id must be lowercase letters, numbers, underscores. Got: '{v}'"
            )
        return v
    
    @field_validator("argument")
    @classmethod
    def validate_argument_specificity(cls, v: str) -> str:
        """Encourage concise, specific arguments that cite evidence.
        
        Arguments should ideally:
        - Be under 500 characters for readability
        - Cite file paths or line numbers when possible
        - Avoid repetition
        """
        v = v.strip()
        if len(v) > 2000:
            # Warn but don't fail - some complex cases may need more space
            # But encourage conciseness
            pass
        return v


# ──────────────────────────────────────────────
# Chief Justice Output (internal model)
#
# AuditReport and CriterionResult are used INSIDE
# the chief_justice node for structured validation.
# The node serializes AuditReport to Markdown and
# puts the string in state["final_report"].
# ──────────────────────────────────────────────


class CriterionResult(BaseModel):
    """Result for a single rubric dimension after synthesis.

    Combines all three judge opinions and records which
    synthesis rule was applied (security override, consensus, etc.).
    """

    dimension_id: str = Field(description="Rubric dimension ID")
    dimension_name: str = Field(description="Human-readable dimension name")
    final_score: int = Field(ge=1, le=5, description="Final synthesized score")
    judge_opinions: list[JudicialOpinion] = Field(
        description="All three judge opinions for this criterion"
    )
    rules_fired: list[str] = Field(
        default_factory=list,
        description="Which synthesis rules triggered (e.g., 'security_override', 'consensus')",
    )
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Required when score variance > 2",
    )
    remediation: str = Field(
        default="",
        description="Specific file-level fix instructions",
    )

    @field_validator("judge_opinions")
    @classmethod
    def validate_three_judges(cls, v: list[JudicialOpinion]) -> list[JudicialOpinion]:
        """All three judge personas must be present."""
        if len(v) != 3:
            raise ValueError(f"Must have exactly 3 opinions, got {len(v)}")
        judges = {op.judge for op in v}
        required = {"Prosecutor", "Defense", "TechLead"}
        if judges != required:
            raise ValueError(f"Need all three judges {required}, got {judges}")
        return v

    @model_validator(mode="after")
    def check_dissent_required(self):
        """Dissent summary is required when judges disagree by > 2 points."""
        scores = [op.score for op in self.judge_opinions]
        variance = max(scores) - min(scores)
        if variance > 2 and not self.dissent_summary:
            raise ValueError(
                f"Score variance {variance} > 2 (scores: {scores}) "
                "requires a dissent_summary"
            )
        return self


class AuditReport(BaseModel):
    """Complete audit report. Built by chief_justice, then serialized to Markdown.

    This model is NOT stored directly in AgentState. The chief_justice
    builds it, validates it, calls to_markdown(), and puts the Markdown
    string into state["final_report"].
    """

    repo_url: str
    git_commit_hash: str = ""
    model_metadata: dict = Field(default_factory=dict)
    overall_score: float = Field(ge=1.0, le=5.0)
    executive_summary: str = Field(min_length=50)
    criteria: list[CriterionResult]
    remediation_plan: str = Field(min_length=50)

    @model_validator(mode="after")
    def check_score_consistency(self):
        """Overall score should be close to the average of criterion scores."""
        if not self.criteria:
            raise ValueError("Report must have at least one criterion result")
        avg = sum(c.final_score for c in self.criteria) / len(self.criteria)
        if abs(self.overall_score - avg) > 1.0:
            raise ValueError(
                f"overall_score ({self.overall_score}) too far from "
                f"criterion average ({avg:.2f})"
            )
        return self

    def to_markdown(self) -> str:
        """Serialize the report to Markdown for state['final_report'].

        This is the method the chief_justice calls before writing to state.
        """
        # The executive_summary string already includes the top-level
        # report header, audit metadata table, and its own
        # "## Executive Summary" section (including score stats).
        #
        # Here we simply append the per-criterion breakdown and the
        # remediation plan underneath that pre-built summary to avoid
        # duplicating headers/metadata in the final Markdown report.
        lines = [
            self.executive_summary,
            "",
        ]

        for criterion in self.criteria:
            scores = [op.score for op in criterion.judge_opinions]
            lines.append(f"## {criterion.dimension_name} — Score: {criterion.final_score}/5")
            lines.append("")
            lines.append("### Judicial Opinions")

            for op in criterion.judge_opinions:
                lines.append(f"- **{op.judge}** (Score: {op.score}/5): {op.argument}")
            lines.append("")

            if criterion.rules_fired:
                lines.append(f"### Rules Applied: {', '.join(criterion.rules_fired)}")
                lines.append("")

            if criterion.dissent_summary:
                lines.append("### Dissent")
                lines.append(criterion.dissent_summary)
                lines.append("")

            if criterion.remediation:
                lines.append("### Remediation")
                lines.append(criterion.remediation)
                lines.append("")

            lines.append("---")
            lines.append("")

        lines.append(self.remediation_plan)

        return "\n".join(lines)


# ──────────────────────────────────────────────
# Graph State
#
# This is the TypedDict that flows through every node.
# Fields with Annotated reducers support parallel writes.
# ──────────────────────────────────────────────


class AgentState(TypedDict):
    """Shared state for the LangGraph pipeline.
    
    Reducers prevent parallel agents from overwriting each other:
    - operator.ior merges evidence dicts from 3 detectives
    - operator.add concatenates opinion lists from 3 judges
    
    Every field is required. Initialize with defaults at invoke time:
        graph.invoke({
            "repo_url": url,
            "pdf_path": path,
            "rubric_path": "rubric.json",
            "git_commit_hash": "",
            "model_metadata": {},
            "rubric_dimensions": [],
            "synthesis_rules": {},
            "evidences": {},
            "opinions": [],
            "final_report": "",
            "repo_root": "",
        })
    """
    
    # ── Input (set at invoke) ──
    repo_url: str
    pdf_path: str
    rubric_path: str
    
    # ── Metadata (set during execution) ──
    git_commit_hash: str
    model_metadata: dict
    # Absolute path to the cloned repository root (set by repo_investigator).
    # This allows other nodes (e.g., doc_analyst) to locate artifacts such as
    # reports/interim_report.* inside the sandboxed clone.
    repo_root: str
    
    # ── Configuration (set by context_builder) ──
    rubric_dimensions: list[dict]
    synthesis_rules: dict
    
    # ── Parallel execution (reducers required) ──
    evidences: Annotated[dict[str, list[Evidence]], operator.ior]
    opinions: Annotated[list[JudicialOpinion], operator.add]
    
    # ── Output (set by chief_justice as Markdown string) ──
    final_report: str
    
    # ── Error handling ──
    error_state: str  # "none", "context_error", "detective_error", "judge_error", "synthesis_error"
    error_message: str  # Human-readable error description