from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.app.core.exceptions import AppException
from backend.app.schemas.error import ErrorResponse, ErrorDetail
from backend.app.core.logging import logger
import traceback

def register_exception_handlers(app: FastAPI):
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        if exc.status_code >= 500:
            logger.error(f"Application error: {exc.code} - {exc.message} - {exc.details}")
        else:
            logger.warning(f"Application error: {exc.code} - {exc.message} - {exc.details}")
            
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_resp.model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.method} {request.url}: {exc.errors()}")
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                details=[{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
            )
        )
        return JSONResponse(
            status_code=422,
            content=error_resp.model_dump()
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP exception {exc.status_code} on {request.method} {request.url}: {exc.detail}")
        
        # Try to extract code from detail if it's a dict
        code = "HTTP_ERROR"
        message = str(exc.detail)
        details = None
        
        if isinstance(exc.detail, dict):
            message = exc.detail.get("message", "HTTP Error")
            code = exc.detail.get("code", f"HTTP_{exc.status_code}")
            details = exc.detail
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 400:
            code = "BAD_REQUEST"
        
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
                details=details
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_resp.model_dump()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}\n{traceback.format_exc()}")
        error_resp = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred.",
                details=None
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_resp.model_dump()
        )
