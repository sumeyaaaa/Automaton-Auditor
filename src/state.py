"""
State definitions for the Automaton Auditor.
Uses Pydantic models and TypedDict with reducers for safe parallel execution.
"""
import operator
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# --- Detective Output ---


class Evidence(BaseModel):
    """Structured evidence collected by forensic agents.
    
    Detectives collect facts only - no opinions, no scores.
    All evidence must be backed by objective verification.
    """

    criterion_id: str = Field(
        description="ID of the rubric dimension this evidence addresses"
    )
    goal: str = Field(
        description="The specific forensic goal this evidence addresses"
    )
    found: bool = Field(
        description="Whether the artifact exists (binary fact, not judgment)"
    )
    content: Optional[str] = Field(
        default=None,
        description="Extracted content or code snippet (factual data only)",
    )
    location: str = Field(
        description="File path, commit hash, or other location identifier"
    )
    rationale: str = Field(
        description="Rationale for confidence in the evidence found for this goal. "
        "Must explain the forensic method used (e.g., 'AST confirmed', 'git log extracted')"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1, must be justified by rationale",
    )


# --- Judge Output ---


class JudicialOpinion(BaseModel):
    """Opinion rendered by a judge persona on a specific criterion.
    
    Judges interpret evidence and assign scores based on their persona:
    - Prosecutor: Critical lens, focuses on gaps and security
    - Defense: Optimistic lens, rewards effort and intent
    - Tech Lead: Pragmatic lens, evaluates functionality
    """

    judge: Literal["Prosecutor", "Defense", "TechLead"] = Field(
        description="The judicial persona rendering this opinion"
    )
    criterion_id: str = Field(
        description="ID of the rubric criterion being evaluated (must match dimension id)"
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Score from 1 to 5 based on rubric scale",
    )
    argument: str = Field(
        description="Reasoning for this score with specific file citations and evidence references"
    )
    cited_evidence: List[str] = Field(
        default_factory=list,
        description="List of evidence locations or IDs referenced in this opinion",
    )


# --- Chief Justice Output ---


class CriterionResult(BaseModel):
    """Final result for a single rubric criterion after synthesis.
    
    Combines all three judge opinions and applies deterministic synthesis rules
    to produce a final score and actionable remediation.
    """

    dimension_id: str = Field(description="ID of the rubric dimension")
    dimension_name: str = Field(description="Human-readable name of the dimension")
    final_score: int = Field(
        ge=1, le=5, description="Final synthesized score after applying synthesis rules"
    )
    judge_opinions: List[JudicialOpinion] = Field(
        description="All three judge opinions (Prosecutor, Defense, TechLead) for this criterion"
    )
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Summary of disagreement when score variance > 2. "
        "Required when judges disagree significantly.",
    )
    remediation: str = Field(
        description="Specific file-level instructions for improvement. "
        "Must be actionable and cite specific files/paths."
    )


class AuditReport(BaseModel):
    """Final audit report structure.
    
    Complete audit report with executive summary, per-criterion breakdown,
    and comprehensive remediation plan.
    """

    repo_url: str = Field(description="URL of the audited repository")
    executive_summary: str = Field(
        description="High-level summary of findings including metadata, overall score, and key issues"
    )
    overall_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Weighted average of all criterion scores",
    )
    criteria: List[CriterionResult] = Field(
        description="Detailed results for each rubric criterion"
    )
    remediation_plan: str = Field(
        description="Comprehensive remediation plan with prioritized actions grouped by severity"
    )


# --- Graph State ---


class AgentState(TypedDict, total=False):
    """Main state object for the LangGraph workflow.
    
    Uses Annotated reducers to prevent parallel agents from overwriting data:
    - operator.ior for dict merge (evidences) - merges dictionaries from parallel detectives
    - operator.add for list concatenation (opinions) - concatenates lists from parallel judges
    
    Fields marked with total=False are optional and can be added during execution.
    """

    # Input fields (set at invoke)
    repo_url: str
    pdf_path: str

    # Metadata fields (set during execution)
    git_commit_hash: str  # Set by repo_investigator
    model_metadata: Dict  # Set by graph initialization (from config)

    # Configuration (set at graph creation)
    rubric_dimensions: List[Dict]  # Loaded from rubric JSON

    # Parallel execution fields (use reducers)
    evidences: Annotated[
        Dict[str, List[Evidence]], operator.ior
    ]  # Dict merge: {"repo": [...], "doc": [...], "vision": [...]}
    opinions: Annotated[
        List[JudicialOpinion], operator.add
    ]  # List concat: [p1, p2, ...] + [d1, d2, ...] + [t1, t2, ...]

    # Synthesis configuration
    synthesis_rules: Dict  # Loaded from rubric JSON for Chief Justice

    # Output field (set by Chief Justice)
    final_report: Optional[AuditReport]
