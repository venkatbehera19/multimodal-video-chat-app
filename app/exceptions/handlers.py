import asyncio
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.log_config import logger
from app.exceptions.domain import AppError

from starlette.exceptions import HTTPException as StarletteHTTPException

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
  """Handle domain AppError and subclasses (response shape from domain).

  Args:
    request: The FastAPI request.
    exc: The domain AppError instance.

  Returns:
    JSONResponse with status_code and content from exc.to_response_content().
  """
  return JSONResponse(
    status_code = exc.status_code,
    content= exc.to_response_content(request.url.path)
  )
  
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
  """Catch-all for unhandled exceptions; log and return safe 500 response.

  Args:
    request: The FastAPI request.
    exc: The unhandled exception.

  Returns:
    JSONResponse with 500 status and generic error message.
  """

  logger.exception(
    "Unhandled exception",
    extra={"path": request.url.path, "method": request.method},
  )

  return JSONResponse(
    status_code=500,
    content={
      "error": {
          "code": "internal_server_error",
          "message": "Internal Server Error",
      },
      "path": request.url.path,
    },
  )