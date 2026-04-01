class AppError(Exception):
  """Base application error with HTTP status and error code."""

  status_code: int = 500
  code: str = "internal_error"

  def __init__(self, message: str) -> None:
    """Initialize AppError with a message.

    Args:
      message: Human-readable error description.
    """
    super().__init__(message)
    self.message = message

  def to_response_content(self, path: str) -> dict:
    """Build the JSON body for this error (used by handlers).

    Args:
      path: Request path for the response.

    Returns:
      Dict with error code, message, and path.
    """
    return {
      "error": { "code": self.code, "message": self.message },
      "path": path,
    }
  

class NotFoundError(AppError):
  """Resource not found"""
  status_code: int = 404
  code: str = "not_found"

class InternalServerError(AppError):
  """Unexpected internal error (e.g. DB, I/O)."""
  status_code: int = 500
  code: str = "internal_error"

class ValidationError(AppError):
  """Domain or request validation failed."""
  status_code: int = 422
  code: str = "validation_error"