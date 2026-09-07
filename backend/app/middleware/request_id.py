import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique request ID to each incoming HTTP request,
    measuring duration and setting the X-Request-ID response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = f"req_{uuid.uuid4().hex[:16]}"

        request.state.request_id = req_id
        request.state.start_time = time.time()

        response = await call_next(request)

        response.headers["X-Request-ID"] = req_id
        duration_ms = round((time.time() - request.state.start_time) * 1000, 2)
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response
