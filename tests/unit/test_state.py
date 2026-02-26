"""Unit tests for state models."""
import pytest

from src.state import AgentState, Evidence, JudicialOpinion


class TestEvidence:
    """Test Evidence model."""

    def test_evidence_creation(self):
        """Test creating an Evidence object."""
        evidence = Evidence(
            criterion_id="test_criterion",
            goal="Test goal",
            found=True,
            content="Test content",
            location="test/location.py",
            rationale="Test rationale",
            confidence=0.9,
        )
        assert evidence.criterion_id == "test_criterion"
        assert evidence.found is True
        assert evidence.confidence == 0.9

    def test_evidence_confidence_bounds(self):
        """Test confidence bounds validation."""
        # Valid confidence
        evidence = Evidence(
            criterion_id="test",
            goal="test",
            found=True,
            location="test",
            rationale="test",
            confidence=0.5,
        )
        assert evidence.confidence == 0.5

        # Invalid confidence (too high)
        with pytest.raises(Exception):
            Evidence(
                criterion_id="test",
                goal="test",
                found=True,
                location="test",
                rationale="test",
                confidence=1.5,  # > 1.0
            )

        # Invalid confidence (too low)
        with pytest.raises(Exception):
            Evidence(
                criterion_id="test",
                goal="test",
                found=True,
                location="test",
                rationale="test",
                confidence=-0.1,  # < 0.0
            )


class TestJudicialOpinion:
    """Test JudicialOpinion model."""

    def test_opinion_creation(self):
        """Test creating a JudicialOpinion."""
        opinion = JudicialOpinion(
            judge="Prosecutor",
            criterion_id="test_criterion",
            score=3,
            argument="Test argument",
            cited_evidence=["evidence1", "evidence2"],
        )
        assert opinion.judge == "Prosecutor"
        assert opinion.score == 3
        assert len(opinion.cited_evidence) == 2

    def test_opinion_score_bounds(self):
        """Test score bounds validation."""
        # Valid score
        opinion = JudicialOpinion(
            judge="Prosecutor",
            criterion_id="test",
            score=3,
            argument="test",
        )
        assert opinion.score == 3

        # Invalid score (too high)
        with pytest.raises(Exception):
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=6,  # > 5
                argument="test",
            )

        # Invalid score (too low)
        with pytest.raises(Exception):
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=0,  # < 1
                argument="test",
            )

    def test_judge_persona_validation(self):
        """Test judge persona must be one of the allowed values."""
        # Valid personas
        for persona in ["Prosecutor", "Defense", "TechLead"]:
            opinion = JudicialOpinion(
                judge=persona,
                criterion_id="test",
                score=3,
                argument="test",
            )
            assert opinion.judge == persona

        # Invalid persona (if Pydantic validation works)
        # Note: This depends on Pydantic's Literal validation


class TestAgentState:
    """Test AgentState TypedDict."""

    def test_state_creation(self):
        """Test creating AgentState."""
        state: AgentState = {
            "repo_url": "https://github.com/test/repo.git",
            "pdf_path": "test.pdf",
            "rubric_dimensions": [],
            "evidences": {},
            "opinions": [],
        }
        assert state["repo_url"] == "https://github.com/test/repo.git"
        assert isinstance(state["evidences"], dict)




