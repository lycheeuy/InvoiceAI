# Phase 5 Task 6: Invoice Upload and Activity UI Integration

## Objective
Connect the `/upload` and `/activity` pages to the real backend API. The upload interface handles multipart file processing efficiently, and the activity feed accurately polls/retrieves system status metrics without faking database logs.

## Implementations

### Upload Integration
- **Location:** `frontend/app/upload/page.tsx`
- **Architecture:** Transitioned to a React Client Component to manage file selection and HTTP transmission via `uploadInvoice`.
- **States Managed:**
  - Idle state (drag-and-drop / file selector overlay).
  - Selected File metadata (name/size display).
  - Uploading state (locks input bounds).
  - Success state (returns clear `InvoiceUploadResponse` details rendering the exact file ID and initial status).
  - Error state (intercepts `ApiError` mapping directly to UI components avoiding ugly console bursts).
- **Duplicate Handing:** A backend duplicate (409) safely returns the backend's explicit `Duplicate file detected.` warning.

### Activity Integration
- **Location:** `frontend/app/activity/page.tsx`
- **Architecture:** Transitioned to a React Client Component for isolated periodic re-fetching functionality.
- **Processing Status Display:**
  - Lists the 20 most recent invoices leveraging standard `listInvoices`.
  - Injects consistent visual representation via `@/components/ui/badge` identical to the dashboard parameters.
- **Polling Strategy:**
  - Lightweight polling `useEffect` added.
  - Automatically checks `invoices.some(inv => inv.status === 'PENDING' || inv.status === 'EXTRACTING')`. 
  - Iteratively refetches `listInvoices` natively (every 5 seconds) *only* if active tasks are detected. 
  - Terminates polling completely once all results reach a terminal state (`PROCESSED`, `NEEDS_REVIEW`, `FAILED`).
- **Manual Control:** A standard explicit manual refresh `Button` offers immediate cache invalidation. 

## Accessibility
- File input remains hidden functionally behind standard SR-only classes but maintains `label htmlFor` linkages making interaction entirely keyboard-accessible.
- Buttons dynamically attach `disabled={true}` avoiding dual-submissions gracefully.

## Security
- No absolute paths or stack traces surfaced to the browser on bad payloads.
- API requests route exclusively through `NEXT_PUBLIC_API_URL`.

## Testing Results
- **Frontend ESLint:** 0 errors
- **Frontend TypeScript (`tsc`):** Clean compilation.
- **Frontend Build (`npm run build`):** Clean asset generation.
- **Backend Pytest:** 109 tests passed, 0 failures.

## Known Limitations
- The activity feed doesn't stream line-item logs (as the backend embeds this securely inside `InvoiceDetailResponse` per UUID). Thus, global activity restricts itself to recent document statuses. 
- High-volume systems might require paginated/filtered activity rather than just the latest 20 items.

## Exact Next Task
PHASE 5 TASK 7 — INVOICE DETAIL VIEW AND STRUCTURED DATA INTEGRATION
