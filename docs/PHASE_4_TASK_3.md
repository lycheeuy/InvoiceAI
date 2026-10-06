# Phase 4 Task 3: API Validation & Security Hardening

## 1. Objective
Harden the existing FastAPI backend against malformed, abusive, or unexpected input while preserving all valid behavior. Specifically, strict input validation and safe file handling mechanisms were implemented to prevent path traversal, resource exhaustion, and MIME spoofing.

## 2. Existing Security Controls
The following security controls were verified and preserved intact:
- 10 MB file size limit enforced via chunked reading.
- Strict SHA-256 duplicate detection rejecting exact file matches with 409 Conflict.
- Magic-byte validation (`b"%PDF"`, `b"\x89PNG\r\n\x1a\n"`, `b"\xff\xd8\xff"`) verifying the actual physical bytes of the file, rather than trusting headers.

## 3. Upload Security Review
- Ensured file extension maps cleanly to the magic bytes signature.
- Validated that an oversized file is rejected safely during the `CHUNK_SIZE` read phase (without reading the entire file into memory).
- Empty files (0 bytes) continue to be safely rejected.

## 4. Filename/Path Security
- **Path Traversal Mitigated:** Original filename inputs like `../../etc/passwd` or `C:\Windows\System32\cmd.pdf` are neutralized using `os.path.basename(file.filename.replace("\\", "/"))`.
- The storage path safely ignores user-provided filenames, instead utilizing a generated UUID for storage `storage/invoices/<UUID>.<ext>`.
- The sanitized filename (`safe_filename`) is stored as metadata in the DB.

## 5. UUID Validation
- Validated that endpoints mapped to `id: UUID` (e.g., `GET /api/v1/invoices/{id}`) strictly use Pydantic/FastAPI UUID path type conversions.
- Malformed inputs like `/api/v1/invoices/not-a-uuid` are rejected instantly with a standardized `422 Validation Error` and do not reach the database layer, protecting against DB errors or SQL injection attempts.

## 6. Pagination Validation
- The `GET /api/v1/invoices` endpoint explicitly validates pagination fields:
  - `page` >= 1
  - `limit` >= 1 and `limit` <= 100
- This bounds the maximum rows fetched at once to 100, preventing integer underflows or excessive memory usage.

## 7. Request/Query Validation
- Introduced boundary checks for query inputs on `GET /api/v1/invoices`:
  - `status_filter`: Maximum length 50.
  - `vendor`: Maximum length 100.
- Pydantic models automatically reject invalid bodies for all requests before hitting business logic.

## 8. Content-Type/Magic-Byte Validation
- Added a strict check comparing `file.content_type` header to the detected magic-byte expected MIME.
- Example: If a client uploads a file with `.pdf` extension and valid PDF magic bytes, but maliciously sets `Content-Type: image/jpeg`, it is rejected with 415 Unsupported Media Type. This prevents MIME confusion attacks.

## 9. Memory/Resource Considerations
- Retained the `CHUNK_SIZE` (64 KB) streaming read behavior for validation and disk writing.
- Since the total file size limit is bounded at 10 MB, no additional stream abstractions are required at this stage. Unbounded memory loading is avoided.

## 10. Security Headers Decision
- Evaluated HTTP security headers (like `X-Content-Type-Options: nosniff`).
- Given that the backend operates as a pure REST API communicating JSON and does not directly render content or HTML inside a browser, broad header-based security middlewares are not strictly necessary. Content-type strictly validates payloads upon ingress.

## 11. Error Handling Integration
- All validation violations (`RequestValidationError`) strictly output the standardized `ErrorResponse` schema (defined in Phase 4 Task 2), returning safe codes like `VALIDATION_ERROR`, `INVALID_FILE_TYPE`, or `FILE_TOO_LARGE`.
- Internal tracebacks are completely suppressed.

## 12. Tests
- **Existing baseline:** 93
- **New tests:** 5
- **Total:** 98
- **Failed:** 0
- **Skipped:** 0

## 13. Full Test Result
All tests run successfully, covering edge cases for boundary errors, empty payloads, MIME spoofing, large files, and bad UUID paths.

## 14. Security Findings
- The application relies heavily on `fastapi` and `pydantic` capabilities, which are robust.
- No dynamic SQL exists; SQLAlchemy ORM is exclusively used.
- No direct vulnerabilities found beyond the addressed path traversal and MIME spoof vectors.

## 15. Known Limitations
- None affecting the current scope.
- Authentication/Authorization is deferred until explicit project requirements are laid out, meaning API boundaries are currently publicly accessible.

## 16. Files Changed
- `backend/app/api/v1/endpoints/invoices.py`
- `backend/app/services/document.py`
- `backend/app/services/invoice_service.py`
- `backend/tests/test_api_security.py` (New)

## 17. Next Recommended Task
Phase 4 Task 4 — Invoice API Improvements
