# Phase 2 Task 1: Document Processing Core

## Objective
Establish the foundational architecture and core components for the document processing pipeline. This includes defining standardized schemas, base interfaces, a basic PDF text extractor, and a document router.

## Schemas
Defined in `backend/app/services/document_processing/schemas.py`:
- `ProcessingMethod` (Enum): `pdfplumber`, `gemini`
- `DocumentType` (Enum): `digital_pdf`, `scanned_pdf`, `image`
- `DocumentProcessingResult`: Standardized result model capturing extraction metadata (`processing_method`, `document_type`, `extracted_text`, `page_count`, `warnings`, `errors`).

## Base Interface
Defined in `backend/app/services/document_processing/base.py`:
- `DocumentProcessor`: Abstract base class enforcing a uniform `process(file_path)` signature returning a `DocumentProcessingResult`.

## PDF Processor
Defined in `backend/app/services/document_processing/pdf_processor.py`:
- `PdfTextProcessor`: Implements `DocumentProcessor` using `pdfplumber`. 
- Handles standard digital PDFs, iterating through pages, extracting text, and preserving page boundaries natively.

## Document Router
Defined in `backend/app/services/document_processing/router.py`:
- `DocumentRouter`: Routes a document to the appropriate processor based on its extension and content.
- Uses a heuristic approach for PDFs: Attempts extraction using `PdfTextProcessor` first. If the resulting meaningful character count is below a threshold (100 alphanumeric characters), it falls back to the `GeminiDocumentProcessor` (scanned PDF).
- Routes standard images (PNG, JPG, JPEG) directly to `GeminiDocumentProcessor`.

## Testing & Security
- Fully integrated into pytest via later tasks.
- Isolated extraction mechanisms. No external services required for the standard digital PDF processor.

## Limitations
- The `PdfTextProcessor` only extracts text from natively digital PDFs and fails to capture text from purely image-based PDFs without an OCR adapter (which is handled by Gemini).
- Routing heuristic (100 alphanumeric characters) is a simple threshold that may need tuning for edge cases (e.g., highly stylized digital PDFs with low character counts).
