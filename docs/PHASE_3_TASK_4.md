# Phase 3 Task 4 — End-to-End Pipeline Integration

## 1. Objective
This task integrates the previously developed Phase 2 (Document Processing Engine) and Phase 3 components (Structured Invoice Schema, Gemini Extraction, Deterministic Validation) into a cohesive background processing pipeline.

## 2. Previous Components
- **Document Processing (Layer 1):** Routes documents to pdfplumber or Gemini multimodal to extract meaningful raw text.
- **Structured Extraction (Layer 2):** Takes the raw text and utilizes the Gemini API (via structured outputs) to map data accurately into the InvoiceSchema. Gemini is treated as an untrusted semantic parser.
- **Financial Validation (Layer 3):** Determines if the parsed InvoiceSchema represents mathematically consistent financial arithmetic (using Decimal checking against a strict .01 tolerance).

## 3. Integrated Pipeline
The final processing flow is as follows:
1. **Upload** -> Invoice record created in database.
2. **PENDING** -> FastApi returns 202 and adds task to BackgroundTasks.
3. **EXTRACTING** -> Inside background task:
   - *Document Processing:* Extracts text.
   - *Invoice Extraction:* Parses text into structured InvoiceSchema.
   - *Financial Validation:* Verifies arithmetic consistency of the schema.
4. **PROCESSED / NEEDS_REVIEW / FAILED** -> Extracted structured data is persisted in the database and the final status is applied based on the validation result.

## 4. Status Mapping
The final status of an invoice is strictly determined by the outcome of the extraction and validation phases:
- **Extraction failure** -> FAILED (e.g. Gemini returned malformed JSON or a schema violation).
- **Financial validation failure** -> NEEDS_REVIEW (e.g. subtotal + tax != total).
- **Successful validation** -> PROCESSED (The arithmetic perfectly aligns).

Missing optional data (e.g., no tax provided) that skips verification simply flags a warning internally and proceeds to PROCESSED, ensuring valid invoices aren't falsely failed.

## 5. Database Persistence
Extracted data is safely persisted to existing Invoice database columns:
- endor_name, invoice_number, invoice_date, due_date, currency
- Financial numbers: subtotal, 	ax, 	otal (persisted natively as Decimal)
- **Line items:** Recreated dynamically in InvoiceLineItem (recording description, quantity, unit_price, mount).
No floating-point conversions were introduced. All numbers remain Decimal types. 

## 6. Processing Logs
Concise events are created in ProcessingLog indicating system stage success/failures:
- Started document extraction
- Document routing and text processing successful
- Structured extraction successful
- Financial validation completed
- Processing completed successfully
- Processing needs review due to financial inconsistencies
- Failure/Error traces

## 7. Transaction Safety
- Background tasks operate via a fresh, in-process SessionLocal().
- State transitions are logged individually with db.commit() between status transitions (e.g., to ensure EXTRACTING state locks are observable immediately).
- Rollbacks / Failure handles catch pipeline exceptions locally, mark the InvoiceStatus.FAILED.value, log the reason, and safely commit the failed state to the DB.

## 8. BackgroundTasks
The pipeline continues leveraging FastAPI's BackgroundTasks wrapper. The execution is in-process and non-durable as agreed upon for the MVP architecture.

## 9. Testing
- **Number of integration tests added:** 5 Focused tests inside ackend/tests/test_invoice_pipeline_integration.py
- **Total pytest results:** 81 passed, 0 failed, 0 skipped.

## 10. Database Migration
- **Not required.** The current Invoice and InvoiceLineItem schemas possessed sufficient persistence capability. While InvoiceSchema includes deeper nested fields (e.g., endor.address and endor.tax_id), they were mapped safely per the requirements to the existing model (only endor_name was persisted).

## 11. Known Limitations
- Background task architecture is not durable across unexpected server restarts.
- Missing optional deep-data fields on the backend DB (such as endor.address) cannot be currently persisted without a future database migration, as explicitly deferred in the guidelines.
