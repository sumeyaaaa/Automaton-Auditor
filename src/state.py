"""
State definitions for the Automaton Auditor.
Uses Pydantic models and TypedDict with reducers for safe parallel execution.
"""
import operator
import re
from typing import Annotated, Dict, List, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import TypedDict

from src.exceptions import (
    EvidenceValidationError,
    OpinionValidationError,
    StateValidationError,
    ValidationError,
)


# --- Detective Output ---


class Evidence(BaseModel):
    """Structured evidence collected by forensic agents.
    
    Detectives collect facts only - no opinions, no scores.
    All evidence must be backed by objective verification.
    """

    criterion_id: str = Field(
        description="ID of the rubric dimension this evidence addresses",
        min_length=1,
        max_length=100,
    )
    goal: str = Field(
        description="The specific forensic goal this evidence addresses",
        min_length=10,
        max_length=500,
    )
    found: bool = Field(
        description="Whether the artifact exists (binary fact, not judgment)"
    )
    content: Optional[str] = Field(
        default=None,
        description="Extracted content or code snippet (factual data only)",
        max_length=10000,  # Prevent extremely large content
    )
    location: str = Field(
        description="File path, commit hash, or other location identifier",
        min_length=1,
        max_length=500,
    )
    rationale: str = Field(
        description="Rationale for confidence in the evidence found for this goal. "
        "Must explain the forensic method used (e.g., 'AST confirmed', 'git log extracted')",
        min_length=20,
        max_length=2000,
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1, must be justified by rationale",
    )

    @field_validator("criterion_id")
    @classmethod
    def validate_criterion_id(cls, v: str) -> str:
        """Validate criterion ID format."""
        if not v or not v.strip():
            raise EvidenceValidationError("criterion_id", "Criterion ID cannot be empty")
        if not re.match(r"^[a-z0-9_]+$", v):
            raise EvidenceValidationError(
                "criterion_id",
                f"Must contain only lowercase letters, numbers, and underscores. Got: {v}"
            )
        if len(v) > 100:
            raise EvidenceValidationError("criterion_id", f"Exceeds maximum length of 100. Got: {len(v)}")
        return v.strip()

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, v: str) -> str:
        """Validate rationale contains method description."""
        if not v or len(v.strip()) < 20:
            raise EvidenceValidationError(
                "rationale",
                f"Rationale must be at least 20 characters. Got: {len(v) if v else 0}"
            )
        method_keywords = ["AST", "git", "regex", "parsed", "extracted", "verified", "confirmed", "analyzed", "checked"]
        if not any(keyword.lower() in v.lower() for keyword in method_keywords):
            raise EvidenceValidationError(
                "rationale",
                "Must mention the forensic method used (e.g., 'AST confirmed', 'git log extracted')"
            )
        return v.strip()

    @model_validator(mode="after")
    def validate_confidence_rationale(self):
        """Validate that confidence is justified by rationale."""
        if self.confidence > 0.7 and len(self.rationale) < 50:
            raise EvidenceValidationError(
                "confidence",
                "High confidence (>0.7) requires detailed rationale (at least 50 characters). "
                f"Current rationale length: {len(self.rationale)}"
            )
        if self.found and self.confidence < 0.3:
            raise EvidenceValidationError(
                "confidence",
                f"Evidence marked as 'found' should have confidence >= 0.3. Got: {self.confidence}"
            )
        if not self.found and self.confidence > 0.5:
            raise EvidenceValidationError(
                "confidence",
                f"Evidence marked as 'not found' should have confidence <= 0.5. Got: {self.confidence}"
            )
        # Validate content is present when found=True
        if self.found and not self.content and self.confidence > 0.6:
            raise EvidenceValidationError(
                "content",
                "High-confidence evidence marked as 'found' should include content or code snippet"
            )
        return self


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
        description="ID of the rubric criterion being evaluated (must match dimension id)",
        min_length=1,
        max_length=100,
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Score from 1 to 5 based on rubric scale",
    )
    argument: str = Field(
        description="Reasoning for this score with specific file citations and evidence references",
        min_length=50,
        max_length=3000,
    )
    cited_evidence: List[str] = Field(
        default_factory=list,
        description="List of evidence locations or IDs referenced in this opinion",
        max_length=20,  # Prevent excessive citations
    )

    @field_validator("criterion_id")
    @classmethod
    def validate_criterion_id(cls, v: str) -> str:
        """Validate criterion ID format."""
        if not v or not v.strip():
            raise OpinionValidationError("criterion_id", "Criterion ID cannot be empty")
        if not re.match(r"^[a-z0-9_]+$", v):
            raise OpinionValidationError(
                "criterion_id",
                f"Must contain only lowercase letters, numbers, and underscores. Got: {v}"
            )
        return v.strip()

    @field_validator("argument")
    @classmethod
    def validate_argument(cls, v: str) -> str:
        """Validate argument contains citations."""
        if not v or len(v.strip()) < 50:
            raise OpinionValidationError(
                "argument",
                f"Argument must be at least 50 characters. Got: {len(v) if v else 0}"
            )
        # Check for file paths or evidence references
        has_file_reference = bool(re.search(r"(src/|tests/|\.py|\.md|\.json|\.toml|\.yaml)", v))
        has_evidence_reference = bool(re.search(r"(evidence|location|criterion|file|found|content)", v, re.IGNORECASE))
        
        if not (has_file_reference or has_evidence_reference):
            raise OpinionValidationError(
                "argument",
                "Must contain file citations (e.g., 'src/file.py') or evidence references (e.g., 'evidence found at')"
            )
        return v.strip()

    @model_validator(mode="after")
    def validate_score_argument_alignment(self):
        """Validate that score aligns with argument tone."""
        argument_lower = self.argument.lower()
        
        # Low scores should have critical language
        if self.score <= 2:
            critical_keywords = ["missing", "failed", "error", "issue", "problem", "lack", "absent", "incomplete", "weak"]
            if not any(keyword in argument_lower for keyword in critical_keywords):
                raise OpinionValidationError(
                    "score",
                    f"Low scores (1-2) should include critical language. Score: {self.score}, "
                    "argument should mention issues, problems, or missing elements"
                )
        
        # High scores should have positive language
        if self.score >= 4:
            positive_keywords = ["good", "excellent", "proper", "correct", "complete", "well", "strong", "solid", "robust"]
            if not any(keyword in argument_lower for keyword in positive_keywords):
                raise OpinionValidationError(
                    "score",
                    f"High scores (4-5) should include positive language. Score: {self.score}, "
                    "argument should mention strengths, completeness, or quality"
                )
        
        # Validate cited_evidence matches argument
        if self.cited_evidence and len(self.cited_evidence) > 0:
            # Check if cited evidence locations are mentioned in argument
            evidence_mentioned = any(
                any(cite.lower() in argument_lower for cite in self.cited_evidence)
                for _ in [True]
            )
            if not evidence_mentioned and len(self.cited_evidence) > 2:
                # Warning: many citations but none mentioned in argument
                pass  # Not an error, but could be improved
        
        return self


# --- Chief Justice Output ---


class CriterionResult(BaseModel):
    """Final result for a single rubric criterion after synthesis.
    
    Combines all three judge opinions and applies deterministic synthesis rules
    to produce a final score and actionable remediation.
    """

    dimension_id: str = Field(
        description="ID of the rubric dimension",
        min_length=1,
        max_length=100,
    )
    dimension_name: str = Field(
        description="Human-readable name of the dimension",
        min_length=5,
        max_length=200,
    )
    final_score: int = Field(
        ge=1, le=5, description="Final synthesized score after applying synthesis rules"
    )
    judge_opinions: List[JudicialOpinion] = Field(
        description="All three judge opinions (Prosecutor, Defense, TechLead) for this criterion",
        min_length=3,
        max_length=3,
    )
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Summary of disagreement when score variance > 2. "
        "Required when judges disagree significantly.",
        max_length=1000,
    )
    remediation: str = Field(
        description="Specific file-level instructions for improvement. "
        "Must be actionable and cite specific files/paths.",
        min_length=50,
        max_length=2000,
    )

    @field_validator("dimension_id")
    @classmethod
    def validate_dimension_id(cls, v: str) -> str:
        """Validate dimension ID format."""
        if not v or not v.strip():
            raise ValidationError("Dimension ID cannot be empty", {"field": "dimension_id"})
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValidationError(
                f"Dimension ID must contain only lowercase letters, numbers, and underscores. Got: {v}",
                {"field": "dimension_id", "value": v}
            )
        return v.strip()

    @field_validator("judge_opinions")
    @classmethod
    def validate_judge_opinions(cls, v: List[JudicialOpinion]) -> List[JudicialOpinion]:
        """Validate that all three judge opinions are present and consistent."""
        if len(v) != 3:
            raise ValidationError(
                f"Must have exactly 3 judge opinions, got {len(v)}",
                {"field": "judge_opinions", "count": len(v), "expected": 3}
            )
        
        judges = {opinion.judge for opinion in v}
        required_judges = {"Prosecutor", "Defense", "TechLead"}
        if judges != required_judges:
            raise ValidationError(
                f"Must have opinions from all three judges: {required_judges}. Got: {judges}",
                {"field": "judge_opinions", "required": required_judges, "got": judges}
            )
        
        # Ensure all opinions reference the same criterion
        criterion_ids = {opinion.criterion_id for opinion in v}
        if len(criterion_ids) > 1:
            raise ValidationError(
                f"All opinions must reference the same criterion. Got: {criterion_ids}",
                {"field": "judge_opinions", "criterion_ids": list(criterion_ids)}
            )
        
        # Validate score range consistency
        scores = [opinion.score for opinion in v]
        if min(scores) < 1 or max(scores) > 5:
            raise ValidationError(
                f"All scores must be between 1 and 5. Got: {scores}",
                {"field": "judge_opinions", "scores": scores}
            )
        
        return v

    @model_validator(mode="after")
    def validate_dissent_summary(self):
        """Validate dissent summary is present when needed."""
        scores = [opinion.score for opinion in self.judge_opinions]
        score_variance = max(scores) - min(scores)
        
        if score_variance > 2 and not self.dissent_summary:
            raise ValidationError(
                f"Score variance ({score_variance}) > 2 requires a dissent_summary. "
                f"Scores: {scores}",
                {"field": "dissent_summary", "score_variance": score_variance, "scores": scores}
            )
        
        if score_variance > 2 and self.dissent_summary:
            # Validate dissent summary quality
            if len(self.dissent_summary.strip()) < 50:
                raise ValidationError(
                    "Dissent summary must be at least 50 characters when score variance > 2",
                    {"field": "dissent_summary", "length": len(self.dissent_summary)}
                )
        
        # Validate final_score is within range of judge scores
        if self.final_score < min(scores) or self.final_score > max(scores):
            # Allow synthesis to adjust, but warn if too far
            if abs(self.final_score - (sum(scores) / len(scores))) > 1.5:
                raise ValidationError(
                    f"Final score ({self.final_score}) differs significantly from judge average "
                    f"({sum(scores) / len(scores):.2f}). Scores: {scores}",
                    {"field": "final_score", "final_score": self.final_score, "judge_scores": scores}
                )
        
        return self

    @field_validator("remediation")
    @classmethod
    def validate_remediation(cls, v: str) -> str:
        """Validate remediation contains actionable file references."""
        if not v or len(v.strip()) < 50:
            raise ValidationError(
                f"Remediation must be at least 50 characters. Got: {len(v) if v else 0}",
                {"field": "remediation", "length": len(v) if v else 0}
            )
        
        # Check for file paths
        has_file_path = bool(re.search(r"(src/|tests/|\.py|\.md|\.json|\.toml|\.yaml|\.yml)", v))
        has_action_words = bool(re.search(
            r"(add|create|update|fix|remove|implement|refactor|modify|improve|enhance|replace)",
            v, re.IGNORECASE
        ))
        
        if not has_file_path:
            raise ValidationError(
                "Remediation must cite specific files or paths (e.g., 'src/file.py', 'tests/test_file.py')",
                {"field": "remediation"}
            )
        
        if not has_action_words:
            raise ValidationError(
                "Remediation must contain actionable instructions (add, create, update, fix, implement, etc.)",
                {"field": "remediation"}
            )
        
        return v.strip()


class AuditReport(BaseModel):
    """Final audit report structure.
    
    Complete audit report with executive summary, per-criterion breakdown,
    and comprehensive remediation plan.
    """

    repo_url: str = Field(
        description="URL of the audited repository",
        min_length=10,
        max_length=500,
    )
    executive_summary: str = Field(
        description="High-level summary of findings including metadata, overall score, and key issues",
        min_length=100,
        max_length=5000,
    )
    overall_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Weighted average of all criterion scores",
    )
    criteria: List[CriterionResult] = Field(
        description="Detailed results for each rubric criterion",
        min_length=1,
    )
    remediation_plan: str = Field(
        description="Comprehensive remediation plan with prioritized actions grouped by severity",
        min_length=100,
        max_length=10000,
    )

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Validate repository URL format."""
        if not v or not v.strip():
            raise ValidationError("Repository URL cannot be empty", {"field": "repo_url"})
        
        parsed = urlparse(v.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(
                f"Invalid repository URL format. Must be a valid URL (e.g., https://github.com/user/repo). Got: {v}",
                {"field": "repo_url", "value": v}
            )
        if parsed.scheme not in ["http", "https"]:
            raise ValidationError(
                f"Repository URL must use http or https scheme. Got: {parsed.scheme}",
                {"field": "repo_url", "scheme": parsed.scheme}
            )
        # Validate common repository hosts
        valid_hosts = ["github.com", "gitlab.com", "bitbucket.org", "gitea.com"]
        if not any(host in parsed.netloc.lower() for host in valid_hosts):
            # Warning: not a standard git host, but allow it
            pass
        return v.strip()

    @model_validator(mode="after")
    def validate_overall_score_consistency(self):
        """Validate overall score is consistent with criterion scores."""
        if not self.criteria:
            raise ValidationError(
                "Audit report must have at least one criterion result",
                {"field": "criteria", "count": 0}
            )
        
        # Calculate average of criterion scores
        avg_score = sum(criterion.final_score for criterion in self.criteria) / len(self.criteria)
        
        # Allow some tolerance (0.5 points)
        if abs(self.overall_score - avg_score) > 0.5:
            raise ValidationError(
                f"Overall score ({self.overall_score}) differs significantly from "
                f"average criterion score ({avg_score:.2f}). Difference: {abs(self.overall_score - avg_score):.2f}",
                {
                    "field": "overall_score",
                    "overall_score": self.overall_score,
                    "average_score": avg_score,
                    "difference": abs(self.overall_score - avg_score)
                }
            )
        
        # Validate all criteria have valid scores
        for criterion in self.criteria:
            if criterion.final_score < 1 or criterion.final_score > 5:
                raise ValidationError(
                    f"Criterion '{criterion.dimension_id}' has invalid score: {criterion.final_score}",
                    {"field": "criteria", "criterion_id": criterion.dimension_id, "score": criterion.final_score}
                )
        
        return self

    @field_validator("executive_summary")
    @classmethod
    def validate_executive_summary(cls, v: str) -> str:
        """Validate executive summary contains key information."""
        if not v or len(v.strip()) < 100:
            raise ValidationError(
                f"Executive summary must be at least 100 characters. Got: {len(v) if v else 0}",
                {"field": "executive_summary", "length": len(v) if v else 0}
            )
        
        # Check for score mention
        has_score = bool(re.search(r"(score|rating|grade|overall|average)", v, re.IGNORECASE))
        # Check for key findings
        has_findings = bool(re.search(
            r"(finding|issue|problem|strength|weakness|recommendation|conclusion|summary)",
            v, re.IGNORECASE
        ))
        
        if not has_score:
            raise ValidationError(
                "Executive summary must mention the overall score or rating",
                {"field": "executive_summary"}
            )
        
        if not has_findings:
            raise ValidationError(
                "Executive summary must include key findings, issues, or recommendations",
                {"field": "executive_summary"}
            )
        
        return v.strip()

    @field_validator("remediation_plan")
    @classmethod
    def validate_remediation_plan(cls, v: str) -> str:
        """Validate remediation plan has structure."""
        if not v or len(v.strip()) < 100:
            raise ValidationError(
                f"Remediation plan must be at least 100 characters. Got: {len(v) if v else 0}",
                {"field": "remediation_plan", "length": len(v) if v else 0}
            )
        
        # Check for priority indicators
        has_priority = bool(re.search(
            r"(priority|critical|high|medium|low|urgent|important|severe|major|minor)",
            v, re.IGNORECASE
        ))
        # Check for action items
        has_actions = bool(re.search(
            r"(action|step|task|implement|fix|add|create|update|refactor|improve)",
            v, re.IGNORECASE
        ))
        
        if not has_priority:
            raise ValidationError(
                "Remediation plan must include priority levels or severity groupings (critical, high, medium, low)",
                {"field": "remediation_plan"}
            )
        
        if not has_actions:
            raise ValidationError(
                "Remediation plan must include actionable steps or tasks (action, step, task, implement, fix, etc.)",
                {"field": "remediation_plan"}
            )
        
        return v.strip()


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
