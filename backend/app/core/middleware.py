import time
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

# Configure Structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request details (method, path, processing duration, and response status).
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # Process the request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log backend crash/unhandled exception
            process_time = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=process_time,
                status_code=500
            )
            raise exc

        process_time = int((time.perf_counter() - start_time) * 1000)
        
        # Log request summary
        # Note: user_id is injected in request.state if authenticated
        user_id = getattr(request.state, "user_id", "unauthenticated")
        logger.info(
            "request_processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=process_time,
            user_id=str(user_id)
        )
        
        return response
