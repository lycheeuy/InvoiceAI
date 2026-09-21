# Phase 2 Task 2: Gemini Multimodal Adapter

## Objective
Implement a document processing adapter using Gemini to extract text from multimodal document sources (PNG, JPG, JPEG, scanned PDFs). This processor ensures we can extract raw text from image-based invoices and scanned documents for later processing, without relying solely on simple PDF text extractors.

## Relationship with DocumentProcessor
The `GeminiDocumentProcessor` implements the `DocumentProcessor` base class interface. It guarantees that any process invoking it receives a standard `DocumentProcessingResult`, maintaining compatibility with Phase 1 architectures and keeping the extraction method isolated from subsequent logic.

## Supported Document Types
- Images: `.png`, `.jpg`, `.jpeg`
- Documents: `.pdf` (typically used for scanned PDFs that require OCR/multimodal interpretation)

## Gemini Configuration
Configuration is injected through environment variables handled by `Settings` in `config.py`:
- `GEMINI_API_KEY`: The API key for Google Gen AI.
- `GEMINI_MODEL`: The multimodal model to use (default: `gemini-2.5-flash`).

## Multimodal Processing Approach
The implementation utilizes the current `google-genai` SDK.
1. Documents are uploaded via `client.files.upload`.
2. A straightforward prompt instructs Gemini to strictly "extract all readable text", explicitly requesting that it should *not* summarize or invent content.
3. The response is encapsulated into a `DocumentProcessingResult`.

**Note:** Gemini is being used here purely as a multimodal document-understanding adapter to extract visible text, *not* as the deterministic source of truth for parsed invoice fields. Field extraction will happen subsequently.

## Error Handling
Clear validations and error captures are integrated for:
- File not found
- Unsupported extensions
- Missing API Key
- API failures (caught and logged)
- Empty or malformed responses (treated gracefully with warnings)

Sensitive keys or file paths are kept out of client-facing error structures, focusing rather on debuggability through standardized logging.

## Testing Strategy
Tests are written with `pytest` using `unittest.mock` to ensure no live API calls are made. Tests cover edge cases including missing keys, incorrect file types, missing files, expected success behavior, API down responses, and empty returned texts.

## Security Considerations
- The API key is passed securely via environment variables and is not exposed in logs or resulting outputs.
- Document content is uploaded to Gemini solely for the duration of text extraction.
- Error messages omit sensitive stack traces in returning structures to prevent information leakage.

## Limitations
- We rely on Gemini's token limitations for large or dense multi-page PDFs. Extremely long PDFs might exceed the standard prompt context window.
- Page-by-page mapping is currently obscured because Gemini returns the entire document transcription in a single string response.

## Next Task
Phase 3 will cover deterministic extraction (structured parsing of invoice fields like subtotal, tax, vendor, line items) from the raw text provided by these adapters.
