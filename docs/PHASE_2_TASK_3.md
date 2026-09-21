# Phase 2 Task 3: Processing Service Orchestration

## Objective
Implement a core processing service that orchestrates the invocation of `DocumentRouter` and manages state transitions and processing logs for an `Invoice`. 

## Processing Service Responsibility
The `process_invoice` service handles:
- Fetching an invoice from the database.
- Orchestrating status transitions (`PENDING` -> `EXTRACTING` -> `PROCESSED` or `FAILED`).
- Validating the physical file exists using the stored path.
- Delegating actual extraction to the injected `DocumentRouter`.
- Recording audit trails using the existing `ProcessingLog` model.

**Note:** Invoice field extraction is explicitly NOT part of Task 3. 

## Service Flow
1. Fetch invoice by ID. If not found, abort.
2. Update status to `EXTRACTING`.
3. Log the start of extraction.
4. Resolve `storage_path`. If file is missing, log failure and update status to `FAILED`.
5. Invoke `DocumentRouter.process()`.
6. If extraction succeeds, update status to `PROCESSED`, store raw extracted text, and log success.
7. If extraction fails or yields errors, catch the exception/error, update status to `FAILED`, and record the error message in the processing logs.

## DocumentRouter Integration
The service takes an instance of `DocumentRouter` (via dependency injection) and delegates document selection and routing entirely to it. This avoids duplicating router logic or referencing `PdfTextProcessor`/`GeminiDocumentProcessor` directly inside the service.

## Transaction Handling
The service manages database commits after each meaningful state transition (start, success, failure) so that in a crash, the last known state is accurately reflected in the database.

## Processing Logs
The service records all events in the `processing_logs` table using the existing model.
- It sets `stage="PROCESSING"`.
- It uses `log_level="INFO"` for normal steps and `"ERROR"` for exceptions and extraction failures.
- It uses the `message` field to provide context.

## Testing Approach
Tests are implemented using `unittest.mock` to mock out the `DocumentRouter` instance, avoiding actual Gemini API calls. Tests cover:
- Invoice not found.
- Missing file triggering an intentional failure.
- Successful routing and extraction (asserting status `PROCESSED`).
- Failure in the processor itself (asserting status `FAILED`).
All tests reuse the existing `db_session` fixture from the previous testing infrastructure to avoid creating new SQLAlchemy connections unnecessarily.

## Limitations
- Extraction results (raw text) are temporarily housed in `raw_llm_response` or logs, as we do not yet have field extraction.
- The service operates synchronously.

## Why BackgroundTasks is intentionally NOT included yet
BackgroundTasks introduces asynchronous complexity. This task focuses purely on standardizing the synchronous orchestration and database transitions.

## Next Task
Phase 3 (Task 4) will implement deterministic invoice field extraction from the raw text provided by these adapters and integrate BackgroundTasks/Celery/Redis as needed.
