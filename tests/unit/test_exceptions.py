"""
Unit tests for custom exception hierarchy.
"""
import pytest

from src.exceptions import (
    ASTAnalysisError,
    AutomatonAuditorError,
    ConfigurationError,
    DocumentError,
    EvidenceValidationError,
    GitOperationError,
    InvalidLayerError,
    InvalidRepositoryError,
    MissingAPIKeyError,
    NodeExecutionError,
    OpinionValidationError,
    PDFNotFoundError,
    PDFParseError,
    RepositoryCloneError,
    RubricLoadError,
    SecurityViolationError,
    StateValidationError,
    UnsupportedProviderError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception inheritance and structure."""

    def test_base_exception(self):
        """Test base exception class."""
        error = AutomatonAuditorError("Test message", {"key": "value"})
        assert str(error) == "Test message"
        assert error.message == "Test message"
        assert error.details == {"key": "value"}

    def test_configuration_errors(self):
        """Test configuration error hierarchy."""
        assert issubclass(MissingAPIKeyError, ConfigurationError)
        assert issubclass(InvalidLayerError, ConfigurationError)
        assert issubclass(UnsupportedProviderError, ConfigurationError)
        assert issubclass(ConfigurationError, AutomatonAuditorError)

    def test_repository_errors(self):
        """Test repository error hierarchy."""
        assert issubclass(RepositoryCloneError, RepositoryError)
        assert issubclass(InvalidRepositoryError, RepositoryError)
        assert issubclass(GitOperationError, RepositoryError)
        assert issubclass(RepositoryError, AutomatonAuditorError)

    def test_document_errors(self):
        """Test document error hierarchy."""
        assert issubclass(PDFNotFoundError, DocumentError)
        assert issubclass(PDFParseError, DocumentError)
        assert issubclass(DocumentError, AutomatonAuditorError)

    def test_validation_errors(self):
        """Test validation error hierarchy."""
        assert issubclass(StateValidationError, ValidationError)
        assert issubclass(EvidenceValidationError, ValidationError)
        assert issubclass(OpinionValidationError, ValidationError)
        assert issubclass(ValidationError, AutomatonAuditorError)


class TestSpecificExceptions:
    """Test specific exception classes."""

    def test_missing_api_key_error(self):
        """Test MissingAPIKeyError."""
        error = MissingAPIKeyError("OPENAI_API_KEY")
        assert "OPENAI_API_KEY" in str(error)
        assert error.details["key_name"] == "OPENAI_API_KEY"

    def test_invalid_layer_error(self):
        """Test InvalidLayerError."""
        error = InvalidLayerError("invalid_layer", ["layer1", "layer2"])
        assert "invalid_layer" in str(error)
        assert error.details["layer"] == "invalid_layer"
        assert error.details["valid_layers"] == ["layer1", "layer2"]

    def test_unsupported_provider_error(self):
        """Test UnsupportedProviderError."""
        error = UnsupportedProviderError("anthropic", ["openai", "google"])
        assert "anthropic" in str(error)
        assert error.details["provider"] == "anthropic"
        assert error.details["supported_providers"] == ["openai", "google"]

    def test_repository_clone_error(self):
        """Test RepositoryCloneError."""
        error = RepositoryCloneError("https://github.com/user/repo", "Network timeout")
        assert "https://github.com/user/repo" in str(error)
        assert error.details["repo_url"] == "https://github.com/user/repo"
        assert error.details["reason"] == "Network timeout"

    def test_invalid_repository_error(self):
        """Test InvalidRepositoryError."""
        error = InvalidRepositoryError("invalid://url", "Invalid scheme")
        assert "invalid://url" in str(error)
        assert error.details["repo_url"] == "invalid://url"
        assert error.details["reason"] == "Invalid scheme"

    def test_git_operation_error(self):
        """Test GitOperationError."""
        error = GitOperationError("git log", "Permission denied")
        assert "git log" in str(error)
        assert error.details["operation"] == "git log"
        assert error.details["reason"] == "Permission denied"

    def test_pdf_not_found_error(self):
        """Test PDFNotFoundError."""
        error = PDFNotFoundError("/path/to/missing.pdf")
        assert "/path/to/missing.pdf" in str(error)
        assert error.details["pdf_path"] == "/path/to/missing.pdf"

    def test_pdf_parse_error(self):
        """Test PDFParseError."""
        error = PDFParseError("/path/to/corrupt.pdf", "Invalid PDF structure")
        assert "/path/to/corrupt.pdf" in str(error)
        assert error.details["pdf_path"] == "/path/to/corrupt.pdf"
        assert error.details["reason"] == "Invalid PDF structure"

    def test_node_execution_error(self):
        """Test NodeExecutionError."""
        error = NodeExecutionError("repo_investigator", "Timeout exceeded")
        assert "repo_investigator" in str(error)
        assert error.details["node_name"] == "repo_investigator"
        assert error.details["reason"] == "Timeout exceeded"

    def test_rubric_load_error(self):
        """Test RubricLoadError."""
        error = RubricLoadError("/path/to/rubric.json", "File not found")
        assert "/path/to/rubric.json" in str(error)
        assert error.details["rubric_path"] == "/path/to/rubric.json"
        assert error.details["reason"] == "File not found"

    def test_ast_analysis_error(self):
        """Test ASTAnalysisError."""
        error = ASTAnalysisError("/path/to/file.py", "Syntax error")
        assert "/path/to/file.py" in str(error)
        assert error.details["file_path"] == "/path/to/file.py"
        assert error.details["reason"] == "Syntax error"

    def test_security_violation_error(self):
        """Test SecurityViolationError."""
        error = SecurityViolationError("/path/to/file.py", "os.system() usage")
        assert "/path/to/file.py" in str(error)
        assert error.details["file_path"] == "/path/to/file.py"
        assert error.details["violation_type"] == "os.system() usage"

    def test_state_validation_error(self):
        """Test StateValidationError."""
        error = StateValidationError("repo_url", "Invalid URL format")
        assert "repo_url" in str(error)
        assert error.details["field"] == "repo_url"
        assert error.details["reason"] == "Invalid URL format"

    def test_evidence_validation_error(self):
        """Test EvidenceValidationError."""
        error = EvidenceValidationError("evidence_123", "Missing rationale")
        assert "evidence_123" in str(error)
        assert error.details["evidence_id"] == "evidence_123"
        assert error.details["reason"] == "Missing rationale"

    def test_opinion_validation_error(self):
        """Test OpinionValidationError."""
        error = OpinionValidationError("opinion_456", "Missing citations")
        assert "opinion_456" in str(error)
        assert error.details["opinion_id"] == "opinion_456"
        assert error.details["reason"] == "Missing citations"

