# Phase 3 Task 2: Gemini Structured Invoice Extraction

## Purpose
This task integrates the Gemini LLM to semantically extract information from raw document text into the strictly defined \InvoiceSchema\. The implementation acts as the bridge between the OCR/text-extraction pipeline (Phase 2) and our final structured domain representation.

## Extraction Service
The core logic resides in \InvoiceExtractionService\ (located in \ackend/app/services/invoice_extraction_service.py\). It accepts pre-extracted document text and returns a validated \InvoiceSchema\ instance. 
- It does **not** process files (PDF/Images) directly.
- It does **not** handle database updates or background task scheduling.
- It is solely responsible for textual semantic parsing using the Gemini API.

## Gemini Structured Output
We leverage the official \google-genai\ SDK's structured output capability (\esponse_schema\ configuration) by passing our \InvoiceSchema\. This natively forces the Gemini model to output JSON that structurally conforms to our expectations.

## Relationship with InvoiceSchema
The service intimately relies on the \InvoiceSchema\ established in Task 1.
1. The schema is passed to the Gemini API as the desired JSON shape.
2. The raw JSON string returned by Gemini is parsed using \InvoiceSchema.model_validate_json()\.
3. If the LLM produces data that violates the schema (e.g., negative amounts, malformed dates), Pydantic raises a \ValidationError\, which we handle safely.

## Extraction Prompt Principles
The prompt is engineered to treat Gemini as an *untrusted semantic parser*, not a financial calculator:
- Instructs the LLM to extract **only** information present in the document.
- Explicitly forbids inventing, guessing, or hallucinating values.
- Instructs the LLM to output \
ull\ for missing values.
- Explicitly forbids recalculating inconsistent totals or inferring hidden mathematical data.

## Missing-Value Strategy
Because \InvoiceSchema\ defines fields as \Optional\, Gemini can safely return \
ull\ (which Pydantic converts to \None\) for missing or unreadable information. This ensures our pipeline explicitly tracks missing data rather than substituting artificial zero-values.

## Decimal & Date Handling
- **Decimal**: Gemini outputs numbers or string-encoded numbers in JSON. Pydantic safely coerces these into Python \Decimal\ objects. We never convert to \loat\, preventing precision loss.
- **Date**: Gemini is tasked with identifying dates. Pydantic natively parses valid standard date strings into \datetime.date\.

## Pydantic Validation
Gemini's output is treated as untrusted external input. Pydantic enforces:
- Type correctness
- Non-negative constraints
If validation fails, the service raises a clear \InvoiceExtractionError\.

## Error Handling
The service raises \InvoiceExtractionError\ gracefully for:
- Missing API keys (verified locally before network calls).
- Empty or malformed responses from Gemini.
- Pydantic validation failures.
- Underlying network or API exceptions.
Error messages are clean and avoid exposing API keys or raw invoice contents in standard exception texts.

## Testing & Mocking Strategy
The \genai.Client\ is injected into the service. For unit tests (\	est_invoice_extraction_service.py\), the client is fully mocked. We verify that the prompt is constructed correctly, the response is parsed through Pydantic (simulating valid and invalid JSON), and exceptions are correctly thrown, all without making real network calls.

## Limitations & Separation of Concerns
- **Semantic vs. Deterministic**: Gemini performs semantic extraction. It is intentionally prohibited from balancing the invoice's math.
- **Cross-field Validation**: Deterministic financial validation (e.g., asserting \subtotal + tax == total\) is intentionally excluded here. It will be implemented in a dedicated validator in Task 4.
