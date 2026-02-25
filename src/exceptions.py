"""
Custom exception hierarchy for Automaton Auditor.

Provides granular error classes for better error handling and debugging.
"""


class AutomatonAuditorError(Exception):
    """Base exception for all Automaton Auditor errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# --- Configuration Errors ---


class ConfigurationError(AutomatonAuditorError):
    """Raised when there's a configuration issue."""
    pass


class MissingAPIKeyError(ConfigurationError):
    """Raised when a required API key is missing."""
    
    def __init__(self, key_name: str):
        message = f"Required API key '{key_name}' not found in environment variables."
        super().__init__(message, {"key_name": key_name})


class InvalidLayerError(ConfigurationError):
    """Raised when an invalid layer identifier is provided."""
    
    def __init__(self, layer: str, valid_layers: list):
        message = f"Invalid layer: '{layer}'. Must be one of: {valid_layers}"
        super().__init__(message, {"layer": layer, "valid_layers": valid_layers})


class UnsupportedProviderError(ConfigurationError):
    """Raised when an unsupported LLM provider is specified."""
    
    def __init__(self, provider: str, supported_providers: list = None):
        message = f"Provider '{provider}' is not supported."
        if supported_providers:
            message += f" Supported providers: {supported_providers}"
        super().__init__(message, {"provider": provider, "supported_providers": supported_providers})


# --- Repository Errors ---


class RepositoryError(AutomatonAuditorError):
    """Base exception for repository-related errors."""
    pass


class RepositoryCloneError(RepositoryError):
    """Raised when repository cloning fails."""
    
    def __init__(self, repo_url: str, reason: str):
        message = f"Failed to clone repository '{repo_url}': {reason}"
        super().__init__(message, {"repo_url": repo_url, "reason": reason})


class InvalidRepositoryError(RepositoryError):
    """Raised when a repository is invalid or inaccessible."""
    
    def __init__(self, repo_url: str, reason: str):
        message = f"Invalid repository '{repo_url}': {reason}"
        super().__init__(message, {"repo_url": repo_url, "reason": reason})


class GitOperationError(RepositoryError):
    """Raised when a Git operation fails."""
    
    def __init__(self, operation: str, reason: str):
        message = f"Git operation '{operation}' failed: {reason}"
        super().__init__(message, {"operation": operation, "reason": reason})


# --- Document Processing Errors ---


class DocumentError(AutomatonAuditorError):
    """Base exception for document processing errors."""
    pass


class PDFNotFoundError(DocumentError):
    """Raised when a PDF file is not found."""
    
    def __init__(self, pdf_path: str):
        message = f"PDF file not found: {pdf_path}"
        super().__init__(message, {"pdf_path": pdf_path})


class PDFParseError(DocumentError):
    """Raised when PDF parsing fails."""
    
    def __init__(self, pdf_path: str, reason: str):
        message = f"Failed to parse PDF '{pdf_path}': {reason}"
        super().__init__(message, {"pdf_path": pdf_path, "reason": reason})


# --- Validation Errors ---


class ValidationError(AutomatonAuditorError):
    """Base exception for validation errors."""
    pass


class StateValidationError(ValidationError):
    """Raised when AgentState validation fails."""
    
    def __init__(self, field: str, reason: str):
        message = f"State validation failed for field '{field}': {reason}"
        super().__init__(message, {"field": field, "reason": reason})


class EvidenceValidationError(ValidationError):
    """Raised when Evidence validation fails."""
    
    def __init__(self, evidence_id: str, reason: str):
        message = f"Evidence validation failed for '{evidence_id}': {reason}"
        super().__init__(message, {"evidence_id": evidence_id, "reason": reason})


class OpinionValidationError(ValidationError):
    """Raised when JudicialOpinion validation fails."""
    
    def __init__(self, opinion_id: str, reason: str):
        message = f"Opinion validation failed for '{opinion_id}': {reason}"
        super().__init__(message, {"opinion_id": opinion_id, "reason": reason})


# --- Graph Execution Errors ---


class GraphExecutionError(AutomatonAuditorError):
    """Base exception for graph execution errors."""
    pass


class NodeExecutionError(GraphExecutionError):
    """Raised when a node execution fails."""
    
    def __init__(self, node_name: str, reason: str):
        message = f"Node '{node_name}' execution failed: {reason}"
        super().__init__(message, {"node_name": node_name, "reason": reason})


class RubricLoadError(GraphExecutionError):
    """Raised when rubric loading fails."""
    
    def __init__(self, rubric_path: str, reason: str):
        message = f"Failed to load rubric from '{rubric_path}': {reason}"
        super().__init__(message, {"rubric_path": rubric_path, "reason": reason})


# --- Tool Errors ---


class ToolError(AutomatonAuditorError):
    """Base exception for tool execution errors."""
    pass


class ASTAnalysisError(ToolError):
    """Raised when AST analysis fails."""
    
    def __init__(self, file_path: str, reason: str):
        message = f"AST analysis failed for '{file_path}': {reason}"
        super().__init__(message, {"file_path": file_path, "reason": reason})


class SecurityViolationError(ToolError):
    """Raised when a security violation is detected."""
    
    def __init__(self, file_path: str, violation_type: str):
        message = f"Security violation detected in '{file_path}': {violation_type}"
        super().__init__(message, {"file_path": file_path, "violation_type": violation_type})

