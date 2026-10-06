# Phase 5: Task 2 - Polling / Status Updates & UI Refinements

## 1. Task Objective
Improve the frontend so users can see invoice processing progress after upload without manually refreshing the page. The objective involves adding a polling mechanism to the invoice detail page, improving upload-to-detail navigation flow, refining UI status presentations, and handling terminal processing states effectively.

## 2. Existing API Inspected
The API was inspected (`backend/app/api/v1/endpoints/invoices.py`). It already provides necessary endpoints:
- `GET /invoices/{id}` - Returns full invoice details.
- `GET /invoices/{id}/status` - Lightweight endpoint returning just the processing status, review reason, and confidence score. This is ideal for polling to save bandwidth and DB queries.
**Result**: No backend changes were necessary or implemented.

## 3. Polling Architecture
- **Location**: Polling was implemented entirely on the client-side using `useEffect` within `frontend/src/app/invoices/[id]/page.tsx`.
- **Method**: The component fetches lightweight data from `/invoices/{id}/status` inside a `setInterval`.
- **State Updates**: It selectively updates the `status` string in the UI during progression (e.g., `PENDING` -> `EXTRACTING`). Once a terminal state is reached, it fires a full refetch (`GET /invoices/{id}`) to obtain the complete payload (including extracted line items and logs).

## 4. Polling Interval
- Set to **3000ms** (3 seconds), which provides responsive updates without overwhelming the server.

## 5. Polling Start Condition
- Initiated automatically when the invoice's current status is either `PENDING` or `EXTRACTING`.

## 6. Polling Stop Conditions
- Polling halts immediately when the status becomes one of the terminal states: `PROCESSED`, `NEEDS_REVIEW`, or `FAILED`.
- Polling also halts after **5 consecutive connection/server errors**, ensuring the client gracefully falls back to a manual refresh if the server is permanently down or network is disconnected.

## 7. Cleanup Behavior
- Standard React memory-leak prevention (`clearInterval`) is executed within the `useEffect` cleanup return function, guaranteeing that polling completely halts if the user navigates away or unmounts the component.

## 8. Upload-to-Detail Flow
- The upload UI (`frontend/src/app/upload/page.tsx`) was modified to display exactly the messaging required by the prompt ("Invoice uploaded successfully.", "Processing has been queued.") and present a prominent "View invoice" button that guides the user to the detail page where polling begins.

## 9. Processing Status UI
- A lightweight loading spinner SVG was added to visually indicate active processing (`PENDING` or `EXTRACTING`) alongside line items.
- UI statuses mapped precisely as required:
  - `PENDING` -> Waiting for processing (Detail) / Waiting (List)
  - `EXTRACTING` -> Processing invoice... (Detail) / Processing (List)
  - `PROCESSED` -> Processing completed (Detail) / Processed (List)
  - `NEEDS_REVIEW` -> Invoice requires review (Detail) / Needs Review (List)
  - `FAILED` -> Invoice processing failed (Detail) / Failed (List)
- The review reason is safely presented (if present).
- If processing fails (`FAILED`), the latest `ERROR` log message from the backend processing logs is safely extracted and shown to the user, providing contextual feedback without exposing raw internal exceptions.

## 10. Error Handling
- Polling temporarily tolerates errors (incrementing an internal counter) but cleanly disables itself and displays a safe fallback error ("Connection lost or server error. Please refresh the page manually.") if the threshold (5 errors) is crossed.
- Bypassed no centralized error abstraction (`fetchWithHandleError` preserved entirely).

## 11. UI Refinements
- **Invoice List Page**: Added a "Refresh" button allowing manual checks without auto-refreshing the whole table unnecessarily. Updated status labels.
- **Dashboard**: Enriched to display a summary of the 5 most recent invoices (utilizing existing pagination limits `limit=5`), providing more functionality strictly derived from available API data without fabricating metrics.

## 12. Responsive Behavior
- Verified structural responsiveness (e.g., overflow tables, standard Next.js / Tailwind mobile constraints).

## 13. Backend Changes
- **None**. The API contract adequately fulfilled all functionality.

## 14. Testing Results
- Backend Pytest suite passes fully (109 passed).
- Frontend builds properly following resolution of leftover `frontend/app` conflicts (ensuring `frontend/src/app` takes precedence).

## 15. Known Limitations
- The Dashboard currently has no real-time push events. Aggregate sums or financial stats remain unavailable as no corresponding backend aggregation endpoints exist.
- Polling handles intermittent connection loss but does not employ exponential backoff.

## 16. Exact Next Task
Phase 5 Task 3 - Error Boundaries & Analytics Integrations (or as defined by the overall roadmap).
