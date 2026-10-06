# Phase 5: Task 1 - Frontend Foundation & Dashboard

## Task Objective
Build the initial frontend interface for InvoiceAI to consume the existing backend API. The goal is to provide a UI for invoice upload, list, details, and system status without duplicating any backend logic.

## Existing API Contract Inspected
The following backend endpoints and schemas were verified:
- `GET /api/v1/health`: Used for dashboard system status.
- `POST /api/v1/invoices/upload`: Used for document ingestion. Handles 10MB limit and returns `InvoiceUploadResponse`.
- `GET /api/v1/invoices`: Returns paginated lists (`InvoiceListResponse`).
- `GET /api/v1/invoices/{id}`: Returns full invoice details, line items, and processing logs (`InvoiceDetailResponse`).
- `GET /api/v1/invoices/{id}/status`: Returns lightweight status (`InvoiceStatusResponse`).
- **Error Handling**: `ErrorResponse` containing `code`, `message`, and `details` fields is heavily used.

## Frontend Stack
- **Framework**: Next.js (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS

## Directory Structure
```
frontend/
  src/
    app/
      layout.tsx
      page.tsx               (Dashboard)
      upload/page.tsx        (Upload UI)
      invoices/page.tsx      (Invoice List)
      invoices/[id]/page.tsx (Invoice Detail)
    lib/
      api.ts                 (Centralized API client)
    types/
      api.ts                 (Backend schema mappings)
```

## API Client Architecture
The API client (`src/lib/api.ts`) is designed to:
- Centralize all `fetch()` calls.
- Wrap non-2xx responses into an `ApiError` class containing the standard backend `code` and `message` from `ErrorResponse`.
- Make it easy for components to rely on strong types.

## Type Definitions
`src/types/api.ts` directly mirrors the Python Pydantic models from `backend/app/schemas/invoice.py`, `health.py`, and `error.py`, ensuring `Decimal` becomes `number | null`, and status enums map correctly.

## Component Features

### Dashboard (`/`)
- Displays overall system health (`GET /health`).
- Displays total number of invoices (extracted from `GET /invoices?page=1&limit=1`).

### Upload (`/upload`)
- Provides an interface to upload PDF, JPG, PNG files.
- Checks client-side for 10MB limit.
- Submits `multipart/form-data`.
- Displays standard backend errors and success state.

### Invoice List (`/invoices`)
- Paginated table showing all invoices.
- Colors and human-readable strings applied based on backend `InvoiceStatus` enum.
- Links to individual detail views.

### Invoice Detail (`/invoices/[id]`)
- Displays complete metadata: Vendor, Total, Tax, Subtotal, Dates.
- Shows line items in a dedicated table.
- Displays processing audit logs.
- Highlights "review_reason" if present.

## Processing Status Handling
Statuses are strictly driven by the backend enum but mapped to user-friendly labels in the frontend:
- `PENDING` -> "Waiting for processing"
- `EXTRACTING` -> "Processing invoice"
- `PROCESSED` -> "Processed"
- `NEEDS_REVIEW` -> "Needs review"
- `FAILED` -> "Processing failed"

## Testing Results
- No backend code was modified.
- TypeScript compilation is error-free.
- Next.js build runs successfully.

## Known Limitations
- The frontend currently polls for status updates, or requires manual refresh. A real-time approach (e.g. Server-Sent Events or WebSockets) could be implemented later if the backend supports it.
- Pagination is basic but functional.

## Backend Gaps Discovered
- Dashboard statistics: The API only exposes the total number of invoices via the pagination `total` field. We do not currently have an endpoint for aggregation statistics (e.g., total amount processed, processing success rate).

## Exact Next Task
Phase 5 Task 2 - Polling/Status Updates (or further UI refinements).
