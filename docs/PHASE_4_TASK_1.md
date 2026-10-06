# Phase 4 Task 1 — API Contract & Response Standardization

## 1. Objective
The objective of this task is to standardize the public REST API response contracts of the InvoiceAI backend. By defining explicit Pydantic response models and setting appropriate HTTP status codes, we ensure the API is predictable, consistent, strictly typed, and properly documented via FastAPI's OpenAPI integration. This provides a robust foundation for building frontend consumers.

## 2. Existing Endpoints
The following endpoints were inspected and updated:
- `GET /health`
- `GET /api/v1/health` (Mounted on `api_router` which wraps `health_router`)
- `POST /api/v1/invoices/upload`
- `GET /api/v1/invoices`
- `GET /api/v1/invoices/{id}`
- `GET /api/v1/invoices/{id}/status`

## 3. Response Schemas
We defined explicit public response schemas to abstract away the internal SQLAlchemy models.
- `HealthResponse`: Standardizes the health check payload with `status` and `database` fields.
- `InvoiceUploadResponse`: Standardizes the payload when an invoice is uploaded, clearly indicating it's been queued.
- `InvoiceListResponse` & `InvoiceListItem`: Provides a typed array for lists with total count, page, and limit fields.
- `InvoiceDetailResponse`: Contains detailed fields including lines and logs without exposing internal elements.
- `InvoiceStatusResponse`: Exposes lightweight status information.

## 4. HTTP Status Codes
- `200 OK`: Used for standard GET requests.
- `202 ACCEPTED`: Enforced for `POST /api/v1/invoices/upload` since processing occurs in the background via `BackgroundTasks`.

## 5. Financial Serialization
Decimal financial values (`subtotal`, `tax`, `total`, `unit_price`, `amount`) are represented consistently as strings in JSON. Pydantic naturally coerces them into a loss-free string representation in FastAPI, ensuring that precision is preserved and floating-point errors are avoided during JSON transfer.

## 6. Date Serialization
`date` and `datetime` fields (`invoice_date`, `due_date`, `created_at`, `updated_at`) are automatically serialized into standard ISO 8601 string representations by Pydantic, ensuring compatibility across systems.

## 7. Optional Fields
Fields that are inherently optional (e.g., `vendor_name`, `due_date`, `review_reason`) correctly fallback to JSON `null` when they are absent in the database, preserving proper semantic meaning instead of resorting to empty strings.

## 8. OpenAPI
By applying the `response_model` argument to FastAPI route decorators, we enable precise, automatically generated schema structures within the OpenAPI JSON. This provides clear request/response expectations, including optional fields, enum values, and nested structures.

## 9. Backward Compatibility
The existing structures generally remained intact but were made stricter. The `storage_path` was removed from `InvoiceDetailResponse` to prevent leaking internal backend filesystem metadata. Existing consumers relying on basic JSON access will not break, given that the endpoints functionally behave the same as before.

## 10. Tests
- Added `tests/test_api_contracts.py` to assert correct shape, properties, HTTP status codes, and type safety for each endpoint (including null and Decimal behaviors).

## 11. Known Limitations
- Error architecture is currently fragmented (HTTPExceptions are raised natively rather than wrapped globally). This will be resolved in Phase 4 Task 2.
- The pagination logic returns `page` and `limit`, but advanced link-based pagination or cursors are not yet supported.
