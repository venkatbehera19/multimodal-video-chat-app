import time
from app.config.log_config import logger
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
  """Middleware for intercepting and logging HTTP request/response cycles.

  This class captures the HTTP method, URL path, client IP address, 
  and the total processing time (latency) for every incoming request.
  """

  async def dispatch(self, request, call_next):
    """Processes the request, tracks execution time, and logs the result.

    Args:
      request: The incoming Starlette/FastAPI Request object.
      call_next: A function that passes the request to the next 
          middleware or the final route handler.

      Returns:
        Response: The resulting HTTP response from the application.

      Raises:
        Exception: Re-raises any exceptions caught during the request 
          lifecycle after logging the failure.
    """
    start_time = time.time()
    method = request.method
    url = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    try:
      response = await call_next(request)
      process_time = (time.time() - start_time) * 1000

      logger.info(
        f'{client_ip} - "{method} {url}" '
        f'{response.status_code} ({process_time:.2f}ms)'
      )
      return response
    
    except Exception as e:
      process_time = (time.time() - start_time) * 1000
      logger.exception(
        f'{client_ip} - "{method} {url}" FAILED ({process_time:.2f}ms)'
      )

      raise e
