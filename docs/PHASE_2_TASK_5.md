# Phase 2 Task 5: Testing Documentation

## Testing Objectives
The primary goal of this task was to strengthen the test coverage for the complete Phase 2 document-processing pipeline without introducing regressions or rewriting working implementations. The tests are designed to be deterministic, network-free, and independent, guaranteeing safety from API quotas and external dependencies.

## Test Categories
We expanded the test suite by focusing on the following core areas:
- **PDF Processor Tests**: Validates the extraction logic of `PdfTextProcessor`.
- **Router Tests**: Validates the heuristic logic inside `DocumentRouter` (routing based on file extension and character count).
- **Schema Tests**: Validates `DocumentProcessingResult`, `ProcessingMethod`, and `DocumentType`.
- **Processing Service Tests**: Validates the core extraction orchestration and database transition logic.
- **End-to-End (Integration-Style) Tests**: Validates the entire pipeline from file upload through the background processing queue without using external services.

## PDF Processor Tests
Added comprehensive unit tests for `PdfTextProcessor` (in `test_pdf_processor.py`):
- **Digital PDF containing meaningful text**: Ensures text is extracted and correctly chunked per page.
- **Empty/no-text PDF**: Ensures warnings are appended and handled gracefully without crashing.
- **Missing PDF file**: Ensures `FileNotFoundError` translates to proper error tracking.
- **Corrupt PDF**: Ensures generalized exceptions are captured and propagated as `errors` in the result schema.
- **Mocking**: Handled by patching `pdfplumber.open` to avoid requiring arbitrary binary PDF fixtures on disk.

## Router Tests
Added comprehensive tests for `DocumentRouter` (in `test_document_router.py`):
- **PNG/JPG/JPEG Image Routing**: Verifies they always trigger the Gemini processor.
- **Digital PDF (>= 100 meaningful characters)**: Verifies it falls back to `PdfTextProcessor`.
- **Scanned PDF (< 100 meaningful characters)**: Verifies it initially uses `PdfTextProcessor`, recognizes low character count, and re-routes to Gemini.
- **Unsupported Extensions**: Asserts appropriate `ValueError` is raised.
- **Missing Dependencies**: Asserts that if `GeminiProcessor` isn't injected, appropriate errors trigger when attempting to process images/scanned PDFs.

## Gemini Mocking Strategy
To adhere to the strict "network-free" and "API-key-free" requirements:
- **Unit level**: Replaced `GeminiDocumentProcessor` with standard Python `MagicMock(spec=DocumentProcessor)`. 
- **Integration level**: Safely patched `GeminiDocumentProcessor` class in the `test_e2e_processing.py` to prevent any background tasks from attempting HTTP requests.

## Processing Service & BackgroundTasks Tests
- Validated `test_processing_service.py` to ensure it robustly tests successful processes, pipeline failures (e.g., missing files), and database log insertions.
- Reviewed `test_upload_queues_background_task` inside `test_upload.py`, which correctly asserts that `BackgroundTasks.add_task` is triggered with the expected `invoice_id` upon successful upload.

## Integration-Style Test (End-to-End)
Added `test_e2e_upload_to_processed` inside a new `test_e2e_processing.py` file:
- **Flow**: Upload endpoint -> `PENDING` Invoice created -> Background worker triggered -> Mocked `DocumentRouter` triggered -> Result mapped -> Invoice marked as `PROCESSED`.
- **Execution Boundary**: Since `FastAPI` BackgroundTasks test execution often complicates transactional isolation with in-memory DBs, we explicitly mocked the `BackgroundTasks.add_task` behavior during the upload, then manually executed `process_invoice_background`. 
- **Database Scope**: Patched `SessionLocal` to carefully pass the isolated `db_session` while suppressing `db.close()` so that assertions can safely run against the finalized database state.

## Current Test Count/Result
- **Total tests**: 47
- **Passed**: 47
- **Failed**: 0
- **Skipped**: 0
- **Warnings**: 2 (Pre-existing dependency deprecation warnings related to `fastapi` and `starlette` test client).

## Known Test Limitations
- **Background Tasks Isolation**: Standard FastAPI `TestClient` auto-runs background tasks natively, which can cause connection/transaction locking issues with `sqlite:///:memory:` configurations. The test circumvents this through explicit patching.
- **No Real LLM Verification**: Because Gemini calls are heavily mocked, the exact JSON validation response returned directly from the Google API (Task 3 integration) cannot be definitively validated in the test suite unless integration-level mock payloads are introduced. 
