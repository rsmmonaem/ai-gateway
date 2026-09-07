from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import logger


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform OpenAI-compatible error formatters."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # If detail is already formatted with an "error" key, return directly
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=getattr(exc, "headers", None),
            )

        status_type_map = {
            400: "invalid_request_error",
            401: "authentication_error",
            403: "permission_denied",
            404: "not_found",
            429: "rate_limit_error",
            500: "server_error",
            502: "bad_gateway",
            503: "service_unavailable",
            504: "gateway_timeout",
        }

        err_type = status_type_map.get(exc.status_code, "api_error")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": str(exc.detail),
                    "type": err_type,
                    "param": None,
                    "code": err_type,
                }
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        first_err = exc.errors()[0] if exc.errors() else {"msg": "Validation error", "loc": []}
        loc_str = " -> ".join(str(loc) for loc in first_err.get("loc", []))
        message = f"Invalid request body: {first_err.get('msg')} at {loc_str}"

        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": message,
                    "type": "invalid_request_error",
                    "param": str(first_err.get("loc", [""])[-1]) if first_err.get("loc") else None,
                    "code": "invalid_payload",
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled server exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "An internal server error occurred.",
                    "type": "server_error",
                    "param": None,
                    "code": "internal_error",
                }
            },
        )
