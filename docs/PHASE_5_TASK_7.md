# Phase 5 Task 7: Invoice Detail View and Structured Data Integration

## Objective
Build the invoice detail page (`/invoices/[id]`) to display the complete structured invoice result returned by the backend, including line items, metadata, processing logs, and real-time polling during processing states.

## Implementations

### Invoice Detail Route
- **Location:** `frontend/app/invoices/[id]/page.tsx`
- **Architecture:** Transitioned to a React Client Component to enable client-side interactive polling and state management for a specific invoice view.

### Data Rendering
- **Structured Fields:** Displays invoice number, vendor name, invoice date, due date, subtotal, tax, and total. Properly formats values using currency where available.
- **Line Items:** Iterates through `invoice.line_items` to display an organized table. Implements clear neutral placeholders ("—") when data is missing, preserving raw extraction results securely without fabricating values.
- **File Info:** Renders file name, size (formatted in MB), type, upload timestamp, and an interactive confidence score bar representing AI extraction certainty.
- **Processing Logs:** Iteratively loops over `invoice.logs`, visually mapping log levels (`ERROR`, `WARNING`, `INFO`) to colored UI indicators (`Red`, `Yellow`, `Blue`) and icons. This timeline traces exact backend states securely.
- **Review Reason:** Dedicated warning panel appears securely rendering backend `review_reason` directly if the invoice transitions to `NEEDS_REVIEW` or `FAILED`.

### Polling & Status Behavior
- Utilized an isolated lightweight `useEffect` hook similar to the Activity feed.
- Polls automatically every 5 seconds only when the invoice status is strictly `PENDING` or `EXTRACTING`.
- Prevents infinite recursion by terminating polling immediately upon reaching terminal states (`PROCESSED`, `NEEDS_REVIEW`, `FAILED`).
- Synchronizes status badges directly via the centralized `getStatusBadgeVariant()` utility from the design system.

### Error States
- Integrates the centralized `ApiError` class cleanly, displaying safe `ErrorState` components on API rejections (e.g., 404 Not Found or Invalid UUIDs) rather than breaking the rendering tree.
- A manual `Try Again` loop is safely provided.

## Accessibility
- Proper `<Table>` semantics used for data presentation.
- Title indicators placed appropriately avoiding hidden overflows (`truncate` classes backed by `title` attributes).
- Interactive buttons correctly disable states during active loads avoiding duplicated overlapping state transmissions.

## Security
- No absolute filesystem paths exposed.
- Relies explicitly on the isolated `NEXT_PUBLIC_API_URL` boundary.
- Zero raw stack traces rendered to users, masked cleanly behind UI states.

## Testing Results
- **Frontend ESLint:** 0 errors.
- **Frontend TypeScript (`tsc`):** Clean compilation.
- **Frontend Build (`npm run build`):** Clean asset generation.
- **Backend Pytest:** 109 tests passed, 0 failures.

## Known Limitations
- Modifying or correcting extracted line items directly is not yet implemented (this relates to human-in-the-loop review functionality).
- There is no web-socket real-time push functionality, relying on lightweight HTTP polling. 

## Exact Next Task
PHASE 5 TASK 8 — HUMAN-IN-THE-LOOP REVIEW UI
