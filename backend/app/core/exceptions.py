from typing import Any, Optional

class AppException(Exception):
    """Base class for all application exceptions."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ResourceNotFoundError(AppException):
    def __init__(self, message: str, code: str = "NOT_FOUND", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=404, details=details)


class DuplicateResourceError(AppException):
    def __init__(self, message: str, code: str = "DUPLICATE_RESOURCE", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=409, details=details)


class InvalidRequestError(AppException):
    def __init__(self, message: str, code: str = "INVALID_REQUEST", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=400, details=details)


class ValidationError(AppException):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=422, details=details)


class FileTooLargeError(AppException):
    def __init__(self, message: str, code: str = "FILE_TOO_LARGE", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=413, details=details)


class UnsupportedMediaTypeError(AppException):
    def __init__(self, message: str, code: str = "INVALID_FILE_TYPE", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=415, details=details)


class DatabaseError(AppException):
    def __init__(self, message: str = "Database error occurred.", code: str = "DATABASE_ERROR", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=500, details=details)


class ProcessingError(AppException):
    def __init__(self, message: str, code: str = "PROCESSING_ERROR", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=500, details=details)


class ExternalServiceError(AppException):
    def __init__(self, message: str, code: str = "EXTERNAL_SERVICE_ERROR", details: Optional[Any] = None):
        super().__init__(message, code=code, status_code=502, details=details)
