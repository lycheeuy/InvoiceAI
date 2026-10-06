# Phase 5 Task 8: Human-in-the-Loop Review UI

## Objective
Build a proper Human-in-the-Loop (HITL) review interface for invoices whose processing status is `NEEDS_REVIEW`. This enables a human operator to inspect extracted invoice data and correct invalid or questionable extracted values before the invoice is considered finalized.

## Architecture & API Changes
- **Backend Endpoint**: Implemented `PATCH /api/v1/invoices/{id}` in `backend/app/api/v1/endpoints/invoices.py`.
- **Backend Service**: Extended `InvoiceService` with `update_invoice` which orchestrates updating the database, re-running financial validation (`InvoiceValidationService`), and logging the manual review stage.
- **Transaction Safety**: Operations on `Invoice` and `InvoiceLineItem` use the existing SQLAlchemy session. If any update fails, it rolls back gracefully without leaving partial states.

## Frontend Changes
- **Review UI Component**: Created `InvoiceReviewForm` (`frontend/components/invoice-review-form.tsx`) to handle input tracking for basic metadata and dynamic line items.
- **Detail View Integration**: Added a "Review & Edit" toggle inside `/invoices/[id]/page.tsx` for `NEEDS_REVIEW` invoices, swapping the readonly display for the editable form.
- **Validation Presentation**: The UI reuses the backend's `review_reason` directly instead of duplicating rules on the frontend.
- **API Extension**: Added `updateInvoice` and corresponding schemas to `frontend/lib/api/client.ts`.

## Validation & Status Transition Behavior
1. **Initial**: Invoice is `NEEDS_REVIEW` (due to OCR extraction failure or math mismatch).
2. **Action**: User modifies fields in the frontend and saves.
3. **Validation**: The backend receives the PATCH payload, updates the models in-memory, and runs `InvoiceValidationService`.
4. **Transition**: 
    - If valid: Transitions to `PROCESSED`.
    - If still invalid: Stays `NEEDS_REVIEW` with an updated `review_reason`.
5. **Persistence**: Transaction committed and logs added under `MANUAL_REVIEW`.

## Security Considerations
- UUID validation explicitly bound on the URL.
- Direct status manipulation by frontend is rejected (status logic is exclusively backend-derived based on financial validations).
- Database path injections restricted as storage path is not exposed via the PATCH schema.

## Tests
- The backend suite currently passes (`109 passed`) validating that the core pipelines (Pipeline integrations, Gemini extractions, Financial validations) haven't regressed.
- Frontend compilation (`npm run build` & `npx tsc`) passes without type violations.

## Known Limitations
- The current line item update logic deletes old line items and recreates them, which assigns new UUIDs to line items upon every edit.
- We do not currently handle pagination for line items in the edit form if an invoice were to have thousands of items (MVP assumption).
