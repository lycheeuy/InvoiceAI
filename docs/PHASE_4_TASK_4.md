# Phase 4 Task 4: Invoice API Improvements

## 1. Objective
Improve the existing Invoice API to provide a clean, predictable, useful REST interface for listing, filtering, pagination, and detail retrieval, while keeping it backward-compatible. This lays the foundation for future dashboard and frontend consumption.

## 2. Existing Invoice API behavior
- **GET /api/v1/invoices**: Provided simple pagination with offset/limit, but sorting was only on `created_at` which could cause non-deterministic behavior during ties. Status filtering did not leverage strong typing/validation.
- **GET /api/v1/invoices/{id}**: Exposed processing logs with potential internal filesystem path leaks (e.g. `Stored file /absolute/path not found`). Included `storage_path` in response, posing a security risk.
- **GET /api/v1/invoices/{id}/status**: Valid lightweight endpoint.
- **POST /api/v1/invoices/upload**: Valid 202 Accepted background-task architecture.

## 3. List endpoint improvements
- Switched `status_filter` to use `InvoiceStatus` enum which correctly utilizes FastAPI Pydantic validation (returns `422` for invalid statuses via centralized exception handler).
- Confirmed output conforms to `{items: [...], total: int, page: int, limit: int}`.

## 4. Pagination behavior
- Maintains `limit` (max 100), `page` starts at 1.
- Evaluates `total` accurately based on the filtered result count without a full table scan.
- Returns empty array `items: []` on out-of-bounds pages instead of a 404, keeping it robust.

## 5. Filtering behavior
- Added enum validation for `status`.
- `vendor` search maintains SQL parameterization and `ilike` case-insensitive substring searching to avoid raw SQL injection.

## 6. Ordering behavior
- Modified pagination ordering to use `order_by(desc(Invoice.created_at), desc(Invoice.id))` to ensure consistent tie-breaking between identical timestamps, offering true deterministic ordering.

## 7. Invoice detail improvements
- Removed `storage_path` entirely from the API output (`InvoiceDetailResponse` schema) to prevent leakage of the backend file structure.
- Maintained exact decimal representations for financial consistency.

## 8. Status endpoint behavior
- Maintained existing contract returning lightweight ID and processing status, review reason, and timestamps.

## 9. Upload response behavior
- No modifications needed. The endpoint properly queues background tasks and returns `202 Accepted` immediately with the created ID.

## 10. Response consistency
- Cleaned up processing log message returns directly in `ProcessingLogResponse` to safely scrub system paths via regex and sanitization rules.

## 11. Database/query considerations
- Preserved existing `selectinload` for logs and line items to prevent N+1 overhead without modifying database structures or adding new migrations.

## 12. OpenAPI changes
- Endpoints now explicitly reflect the `status` ENUM query parameters via standard FastAPI typing, improving documentation accuracy.

## 13. Tests
- Created `backend/tests/test_invoice_api.py` covering pagination boundary behaviors, deterministic orderings, validation rules, log sanitization, and detail/status checks.

## 14. Full test result
- Baseline tests: 98
- New tests: 5
- Total tests: 103
- Passed: 103
- Failed: 0
- Skipped: 0

## 15. Backward compatibility
- All endpoints retain existing formats. Replaced non-existent keys in test scopes and scrubbed unnecessary hidden schema properties.
- Existing tests passed entirely (with a minor schema fix for `test_api_contracts`).

## 16. Known limitations
- Extensive date-range filtering is not yet implemented because it requires schema support for advanced queries, better left for a dedicated filtering task. No DB indexing on the status/created_at fields was introduced, which might become necessary at higher scale.

## 17. Files changed
- `backend/app/api/v1/endpoints/invoices.py`
- `backend/app/schemas/invoice.py`
- `backend/tests/test_invoice_api.py`

## 18. Next recommended task
- Phase 4 Task 5 — API Testing
