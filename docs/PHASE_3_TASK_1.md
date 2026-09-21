# Phase 3 Task 1: Structured Invoice Schema

## Purpose
The purpose of the structured invoice schema is to define a strict data contract for invoice data extraction. It serves as the bridge between raw document text (which will later be processed by the Gemini LLM) and our internal domain representation. 

## Schema Hierarchy
The extraction schema is composed of three nested models, built using Pydantic v2:
- **Vendor**: Captures basic vendor information (name, address, tax_id).
- **LineItem**: Represents an individual item in the invoice (description, quantity, unit_price, amount).
- **InvoiceSchema**: The root schema containing invoice-level metadata (invoice_number, invoice_date, due_date, currency, subtotal, tax, total) as well as the vendor details and list of line items.

## Decimal Strategy
All monetary fields (unit_price, mount, subtotal, 	ax, 	otal) and quantity (which may be fractional, e.g., 1.5 hours) are explicitly defined using Python's \Decimal\ type. This prevents floating-point precision loss during serialization and internal calculations. Pydantic v2 handles Decimal natively, serializing these fields to strings in JSON dumps to ensure precision is retained across API boundaries.

## Date Strategy
Date fields (invoice_date, due_date) are represented using \datetime.date\. Pydantic handles structural validation of ISO date formats natively. Complex date normalization (e.g., converting "Oct 5th, 2026" to a standard format) is intentionally omitted here and will be handled by Gemini in the next task.

## Optional and Missing Values Strategy
Invoices legitimately vary in structure; they may omit a due date, tax information, or even line items if the OCR fails. Therefore, all fields in the schemas are defined as \Optional\ with a default of \None\. 
This design intentionally directs the future LLM extraction task to output \
ull\ for missing fields rather than encouraging hallucinated or invented values. 

## Pydantic Validation (Implemented)
At this stage, validation is strictly structural:
- Ensures dates are valid \datetime.date\ values.
- Ensures all numeric amounts and quantities are valid \Decimal\ values.
- Enforces non-negative constraints (\ge=0\) on \quantity\, \unit_price\, \mount\, \subtotal\, \	ax\, and \	otal\ where appropriate.

## Intentionally NOT Validated Yet
Cross-field business logic and deterministic financial validation are intentionally deferred. 
For example, we do **not** validate that:
- \subtotal == sum(line_items.amount)\
- \	otal == subtotal + tax\
These checks belong to a dedicated deterministic financial validation step (Task 3) that runs *after* extraction, ensuring we can track and flag discrepancies between what is printed on the invoice versus calculated reality.

## Relationship with Future Gemini Extraction
This schema represents the JSON schema contract that will be injected into the Gemini API prompt via Structured Outputs. By establishing it beforehand, we ensure the LLM complies with our explicit strict typing and optional constraints.

## Relationship with Future Deterministic Financial Validation
Because this schema enforces base types but not cross-field calculations, the downstream deterministic validation logic will consume an instance of \InvoiceSchema\, perform strict arithmetic, and produce a validation report of any calculation mismatches.
