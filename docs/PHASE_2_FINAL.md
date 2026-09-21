# Phase 2 Final Document: Document Processing Engine

## 1. Phase 2 Objective
The core objective of Phase 2 was to implement a robust, heuristic-driven document extraction pipeline capable of cleanly pulling raw text from a variety of file formats (Digital PDFs, Scanned PDFs, and Images) using an abstracted processor interface.

*Crucially: Phase 2 extracts document text. Phase 2 does NOT perform structured invoice field extraction or arithmetic validation.*

## 2. Architecture
Phase 2 operates immediately after file upload (Phase 1). It utilizes FastAPI's `BackgroundTasks` to asynchronously trigger the `DocumentRouter`. The router analyzes the document to decide whether it can rely on an offline, deterministic text extractor (`pdfplumber`) or if it must rely on a multimodal vision model (`Gemini`) for scanned/image-based files. The results are logged to the PostgreSQL database and the invoice transitions from `PENDING` -> `EXTRACTING` -> `PROCESSED` (or `FAILED`).

## 3. Task 1 — Document Processing Core
- **Components**: Base interfaces (`DocumentProcessor`), routing models (`DocumentProcessingResult`), and `PdfTextProcessor`.
- **Logic**: Digital PDFs are aggressively preferred using `pdfplumber`. The system natively chunks text page-by-page.

## 4. Task 2 — Gemini Multimodal Adapter
- **Components**: `GeminiDocumentProcessor` using the `google-genai` SDK.
- **Logic**: For images (`.png`, `.jpg`) or PDFs with fewer than 100 meaningful alphanumeric characters, the system prompts Gemini purely to transcribe the visible text. This ensures we have plain text available regardless of the document's original state.

## 5. Task 3 — Processing Service
- **Components**: `process_invoice` orchestrator in `services/document_processing/service.py`.
- **Logic**: Wraps the router call in a database transaction, appending deterministic `ProcessingLog` entries at the start of extraction, on success, and on any caught failures.

## 6. Task 4 — BackgroundTasks Integration
- **Components**: `process_invoice_background` and the `POST /api/v1/invoices/upload` endpoint.
- **Logic**: FastAPI endpoints return `HTTP 202` instantly. The background task receives the `invoice_id`, creates an isolated SQL session, processes the document offline, and automatically closes the session, acting as an MVP in-process worker queue.

## 7. Task 5 — Testing
- **Components**: Complete Pytest test suite with isolated mocking.
- **Logic**: Validates the router heuristics, PDF boundary handling, and complete end-to-end processing execution through `BackgroundTasks` by mocking `pdfplumber` and `google-genai`. This guarantees zero API quotas are consumed during standard CI/CD.

## 8. Final Test Result
- **Total tests**: 47
- **Passed**: 47
- **Failed**: 0
- **Network / External Dependencies**: None (Fully mocked).

## 9. Security Considerations
- The Gemini API Key (`GEMINI_API_KEY`) is securely injected via environment variables.
- Prompt injection risks at the LLM level are mitigated by treating Gemini strictly as a text transcription tool during this phase.
- Invoice contents and raw processing responses are kept out of API error traces to prevent data leakage.

## 10. Known Limitations
- **Background Queue**: FastAPI's `BackgroundTasks` runs in-memory. If the server crashes during extraction, the document remains stuck in `PENDING` or `EXTRACTING`. A durable queue (Redis/Celery) is planned only if concurrency demands outgrow this MVP.
- **Gemini Dependency**: Scanned documents heavily rely on Google's uptime.
- **Text vs. Structure**: Currently, the system only pulls out the raw text. It has no understanding of "Total" or "Due Date" yet.

## 11. Current Architecture Flow
1. **Upload**: User submits document via API.
2. **Persistence**: Saved to local disk; database row created (`PENDING`).
3. **Queue**: Task passed to `BackgroundTasks`.
4. **Extraction**: `DocumentRouter` triggers.
5. **Heuristics**:
   - Digital PDF $\ge$ 100 chars $\rightarrow$ `PdfTextProcessor` (pdfplumber)
   - Scanned PDF or Image $\rightarrow$ `GeminiDocumentProcessor`
6. **Completion**: DB updated to `PROCESSED` or `FAILED`.

## 12. Explicit Phase 2 Boundary
The pipeline STOPS at raw text availability. 
**Phase 2 does NOT perform structured invoice field extraction.**

## 13. Next Phase
**Phase 3 (AI Extraction & Validation Pipeline)** will handle taking the raw extracted text from Phase 2, feeding it into a strict Pydantic JSON extraction prompt, parsing the financial fields (subtotal, tax, total, dates), and executing deterministic mathematical validation rules to decide if the invoice needs manual human review.
