# Phase 4 Task 2: Error Handling & Exception Architecture

## 1. Objective
Establish a clean, consistent, and predictable application-level exception architecture for the FastAPI backend, ensuring safe error responses for clients without leaking sensitive internal details.

## 2. Existing Error-Handling Problems Found
- Using Starlette's `HTTPException` throughout the application leaked internal HTTP framework semantics into the service layer.
- Responses were formatted inconsistently (`{"detail": "..."}`).
- Raw error messages or traceback information could potentially be exposed.
- Missing specific error code structure for reliable client-side parsing.

## 3. Exception Architecture
Introduced a custom exception hierarchy inheriting from `AppException` in `backend/app/core/exceptions.py`.
Classes include:
- `ResourceNotFoundError`
- `DuplicateResourceError`
- `InvalidRequestError`
- `ValidationError`
- `FileTooLargeError`
- `UnsupportedMediaTypeError`
- `ProcessingError`
- `ExternalServiceError`
- `DatabaseError`

## 4. Error Response Schema
Added standard schema in `backend/app/schemas/error.py`.
```json
{
    "error": {
        "code": "ERROR_CODE_STRING",
        "message": "Safe public message",
        "details": null
    }
}
```

## 5. Error Code List
- `INVOICE_NOT_FOUND`
- `INVALID_FILE_TYPE`
- `FILE_TOO_LARGE`
- `DUPLICATE_RESOURCE`
- `INVALID_REQUEST`
- `VALIDATION_ERROR`
- `PROCESSING_ERROR`
- `EXTERNAL_SERVICE_ERROR`
- `DATABASE_ERROR`
- `INTERNAL_SERVER_ERROR`

## 6. HTTP Status Mapping
- 404: `ResourceNotFoundError`
- 409: `DuplicateResourceError`
- 400: `InvalidRequestError`
- 413: `FileTooLargeError`
- 415: `UnsupportedMediaTypeError`
- 422: `ValidationError` (handled via `RequestValidationError`)
- 500: `DatabaseError`, `ProcessingError`, unhandled exceptions
- 502: `ExternalServiceError`

## 7. Centralized Exception Handlers
Defined in `backend/app/core/handlers.py` and registered in `main.py`:
- `app_exception_handler`: Formats `AppException` variants.
- `validation_exception_handler`: Formats FastAPI `RequestValidationError` cleanly without leaking internal Pydantic traceback.
- `http_exception_handler`: Normalizes `StarletteHTTPException`.
- `global_exception_handler`: Catches unhandled `Exception` to avoid tracebacks leaking.

## 8. Security Considerations
- The `global_exception_handler` explicitly logs unhandled tracebacks on the server while returning a generic `INTERNAL_SERVER_ERROR` to the client.
- Handlers do not leak database schemas, credentials, or raw Python stack traces.

## 9. Background Processing Error Behavior
Background tasks (like `process_invoice_background`) were carefully avoided; they continue to update internal invoice states (e.g., `FAILED`) rather than surfacing through API-level exceptions, preserving the resilient state-machine pattern.

## 10. OpenAPI Changes
Added standard `responses` specifications containing `ErrorResponse` schema for endpoints, mapping out 400, 404, 409, 413, 415, 422, and 500 scenarios appropriately for `POST /api/v1/invoices/upload`, `GET /api/v1/invoices/{id}`, and `GET /api/v1/invoices/{id}/status`.

## 11. Tests Added
Created `backend/tests/test_error_handling.py` testing:
- Missing invoice (404)
- Uploading invalid file
- OpenAPI contains `ErrorResponse` component
- Validation payload rejections.
Updated existing `test_upload.py` to assert against standard structure (`error.message` instead of `detail`).

## 12. Full Test Result
- **Existing tests:** 88
- **New tests:** 5
- **Total:** 93
- **Failed:** 0
- **Skipped:** 0

## 13. Known Limitations
None

## 14. Files Changed
- `backend/app/main.py`
- `backend/app/schemas/error.py` (New)
- `backend/app/core/exceptions.py` (New)
- `backend/app/core/handlers.py` (New)
- `backend/app/services/document.py`
- `backend/app/services/invoice_service.py`
- `backend/app/api/v1/endpoints/invoices.py`
- `backend/tests/test_error_handling.py` (New)
- `backend/tests/test_upload.py`

## 15. Next Recommended Task
Phase 4 Task 3 — API Validation & Security Hardening
