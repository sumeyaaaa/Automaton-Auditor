"""
Unit tests for Pydantic model validation.
"""
import pytest
from pydantic import ValidationError

from src.state import AuditReport, CriterionResult, Evidence, JudicialOpinion


class TestEvidenceValidation:
    """Test Evidence model validation."""

    def test_valid_evidence(self):
        """Test creating valid evidence."""
        evidence = Evidence(
            criterion_id="git_forensic_analysis",
            goal="Verify atomic commit progression",
            found=True,
            content='{"total_commits": 10}',
            location="git log",
            rationale="AST confirmed git log extraction shows 10 commits with progression",
            confidence=0.9,
        )
        assert evidence.criterion_id == "git_forensic_analysis"
        assert evidence.found is True
        assert evidence.confidence == 0.9

    def test_invalid_criterion_id_format(self):
        """Test invalid criterion ID format."""
        with pytest.raises(ValidationError) as exc_info:
            Evidence(
                criterion_id="Invalid-ID!",
                goal="Test goal",
                found=True,
                location="test",
                rationale="AST confirmed test",
                confidence=0.5,
            )
        assert "lowercase letters, numbers, and underscores" in str(exc_info.value)

    def test_missing_rationale_method(self):
        """Test rationale without method mention."""
        with pytest.raises(ValidationError) as exc_info:
            Evidence(
                criterion_id="test_criterion",
                goal="Test goal",
                found=True,
                location="test",
                rationale="This is just a description without method",
                confidence=0.5,
            )
        assert "forensic method" in str(exc_info.value)

    def test_high_confidence_requires_detailed_rationale(self):
        """Test high confidence requires detailed rationale."""
        with pytest.raises(ValidationError) as exc_info:
            Evidence(
                criterion_id="test_criterion",
                goal="Test goal",
                found=True,
                location="test",
                rationale="AST confirmed",  # Too short
                confidence=0.8,  # High confidence
            )
        assert "detailed rationale" in str(exc_info.value)

    def test_found_evidence_low_confidence(self):
        """Test found evidence with too low confidence."""
        with pytest.raises(ValidationError) as exc_info:
            Evidence(
                criterion_id="test_criterion",
                goal="Test goal",
                found=True,
                location="test",
                rationale="AST confirmed detailed analysis",
                confidence=0.2,  # Too low for found evidence
            )
        assert "confidence >= 0.3" in str(exc_info.value)

    def test_not_found_evidence_high_confidence(self):
        """Test not found evidence with too high confidence."""
        with pytest.raises(ValidationError) as exc_info:
            Evidence(
                criterion_id="test_criterion",
                goal="Test goal",
                found=False,
                location="test",
                rationale="AST confirmed not found",
                confidence=0.6,  # Too high for not found
            )
        assert "confidence <= 0.5" in str(exc_info.value)


class TestJudicialOpinionValidation:
    """Test JudicialOpinion model validation."""

    def test_valid_opinion(self):
        """Test creating valid opinion."""
        opinion = JudicialOpinion(
            judge="Prosecutor",
            criterion_id="state_management_rigor",
            score=3,
            argument="The code in src/state.py uses Pydantic BaseModel correctly, but lacks custom validators",
            cited_evidence=["src/state.py"],
        )
        assert opinion.judge == "Prosecutor"
        assert opinion.score == 3

    def test_invalid_criterion_id_format(self):
        """Test invalid criterion ID format."""
        with pytest.raises(ValidationError) as exc_info:
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="Invalid-ID!",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=[],
            )
        assert "lowercase letters, numbers, and underscores" in str(exc_info.value)

    def test_argument_missing_file_reference(self):
        """Test argument without file or evidence reference."""
        with pytest.raises(ValidationError) as exc_info:
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="This is just a general comment without any file references",
                cited_evidence=[],
            )
        assert "file citations or evidence references" in str(exc_info.value)

    def test_low_score_missing_critical_language(self):
        """Test low score without critical language."""
        with pytest.raises(ValidationError) as exc_info:
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=1,
                argument="The code in src/state.py is well structured and follows best practices",
                cited_evidence=["src/state.py"],
            )
        assert "critical language" in str(exc_info.value)

    def test_high_score_missing_positive_language(self):
        """Test high score without positive language."""
        with pytest.raises(ValidationError) as exc_info:
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=5,
                argument="The code in src/state.py has issues and needs improvement",
                cited_evidence=["src/state.py"],
            )
        assert "positive language" in str(exc_info.value)


class TestCriterionResultValidation:
    """Test CriterionResult model validation."""

    def test_valid_criterion_result(self):
        """Test creating valid criterion result."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=4,
                argument="File src/state.py demonstrates good practices",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py is functional",
                cited_evidence=["src/state.py"],
            ),
        ]
        result = CriterionResult(
            dimension_id="test_criterion",
            dimension_name="Test Criterion",
            final_score=3,
            judge_opinions=opinions,
            remediation="Update src/state.py to add custom validators",
        )
        assert result.dimension_id == "test_criterion"
        assert len(result.judge_opinions) == 3

    def test_missing_judge_opinions(self):
        """Test criterion result with wrong number of opinions."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=["src/state.py"],
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionResult(
                dimension_id="test_criterion",
                dimension_name="Test Criterion",
                final_score=3,
                judge_opinions=opinions,
                remediation="Update src/state.py",
            )
        assert "exactly 3 judge opinions" in str(exc_info.value)

    def test_missing_judge_type(self):
        """Test criterion result missing a judge type."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=4,
                argument="File src/state.py demonstrates good practices",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Prosecutor",  # Duplicate instead of TechLead
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py is functional",
                cited_evidence=["src/state.py"],
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionResult(
                dimension_id="test_criterion",
                dimension_name="Test Criterion",
                final_score=3,
                judge_opinions=opinions,
                remediation="Update src/state.py",
            )
        assert "all three judges" in str(exc_info.value)

    def test_dissent_summary_required(self):
        """Test dissent summary required for high variance."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=1,
                argument="File src/state.py is missing critical features",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=5,
                argument="File src/state.py demonstrates excellent practices",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="test_criterion",
                score=2,
                argument="File src/state.py needs improvement",
                cited_evidence=["src/state.py"],
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionResult(
                dimension_id="test_criterion",
                dimension_name="Test Criterion",
                final_score=2,
                judge_opinions=opinions,
                remediation="Update src/state.py",
            )
        assert "dissent_summary" in str(exc_info.value)

    def test_remediation_missing_file_path(self):
        """Test remediation without file path."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=4,
                argument="File src/state.py demonstrates good practices",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py is functional",
                cited_evidence=["src/state.py"],
            ),
        ]
        with pytest.raises(ValidationError) as exc_info:
            CriterionResult(
                dimension_id="test_criterion",
                dimension_name="Test Criterion",
                final_score=3,
                judge_opinions=opinions,
                remediation="This is just a general comment without file paths",
            )
        assert "cite specific files or paths" in str(exc_info.value)


class TestAuditReportValidation:
    """Test AuditReport model validation."""

    def test_valid_audit_report(self):
        """Test creating valid audit report."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=4,
                argument="File src/state.py demonstrates good practices",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py is functional",
                cited_evidence=["src/state.py"],
            ),
        ]
        criterion = CriterionResult(
            dimension_id="test_criterion",
            dimension_name="Test Criterion",
            final_score=3,
            judge_opinions=opinions,
            remediation="Update src/state.py to add validators",
        )
        report = AuditReport(
            repo_url="https://github.com/user/repo",
            executive_summary="Overall score: 3.0. The repository shows good structure with some areas for improvement.",
            overall_score=3.0,
            criteria=[criterion],
            remediation_plan="Priority 1: Update src/state.py. Priority 2: Add tests.",
        )
        assert report.repo_url == "https://github.com/user/repo"
        assert report.overall_score == 3.0

    def test_invalid_repo_url(self):
        """Test invalid repository URL."""
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                repo_url="not-a-url",
                executive_summary="Overall score: 3.0. Findings show good structure.",
                overall_score=3.0,
                criteria=[],
                remediation_plan="Priority 1: Fix issues.",
            )
        assert "Invalid repository URL format" in str(exc_info.value)

    def test_executive_summary_missing_score(self):
        """Test executive summary without score mention."""
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                repo_url="https://github.com/user/repo",
                executive_summary="The repository shows good structure with some areas for improvement.",
                overall_score=3.0,
                criteria=[],
                remediation_plan="Priority 1: Fix issues.",
            )
        assert "mention the overall score" in str(exc_info.value)

    def test_overall_score_inconsistency(self):
        """Test overall score inconsistent with criterion scores."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py shows proper structure",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py demonstrates good practices",
                cited_evidence=["src/state.py"],
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="test_criterion",
                score=3,
                argument="File src/state.py is functional",
                cited_evidence=["src/state.py"],
            ),
        ]
        criterion = CriterionResult(
            dimension_id="test_criterion",
            dimension_name="Test Criterion",
            final_score=3,
            judge_opinions=opinions,
            remediation="Update src/state.py",
        )
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                repo_url="https://github.com/user/repo",
                executive_summary="Overall score: 1.0. The repository needs significant improvement.",
                overall_score=1.0,  # Inconsistent with criterion score of 3
                criteria=[criterion],
                remediation_plan="Priority 1: Fix issues.",
            )
        assert "differs significantly" in str(exc_info.value)

