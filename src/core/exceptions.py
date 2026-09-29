class OrchestratorError(Exception):
    """Base exception for all AP/AR Orchestrator errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(OrchestratorError):
    """Raised when application configuration is missing or invalid."""
    pass


class DatabaseError(OrchestratorError):
    """Raised when a database operation fails."""
    pass


class ValidationError(OrchestratorError):
    """Raised when data validation fails."""
    pass


class WorkflowError(OrchestratorError):
    """Raised when workflow orchestration encounters an unrecoverable state."""
    pass
