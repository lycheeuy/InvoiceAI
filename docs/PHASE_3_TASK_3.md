# Phase 3 Task 3: Deterministic Financial Validation

## Purpose
This task implements a pure deterministic financial validator for extracted invoices. 
Since the Gemini LLM is treated as an untrusted semantic parser (Phase 3 Task 2) rather than a calculator, this validation layer acts as the absolute source of truth for arithmetic correctness. It verifies that the line items, subtotal, tax, and total printed on the invoice are mathematically consistent.

## Validation Architecture
The core logic is housed in \InvoiceValidationService\ (located in \ackend/app/services/invoice_validation_service.py\).
The architecture strictly enforces:
- **READ → CHECK → REPORT**
- It **does not** call Gemini.
- It **does not** automatically fix inconsistent totals (No auto-correction).
- It consumes an \InvoiceSchema\ and returns a structured \FinancialValidationResult\ containing \is_valid\, \errors\, and \warnings\.

## Validation Categories
1. **Line Item Validation**: Checks if \quantity × unit_price ≈ amount\.
2. **Subtotal Validation**: Checks if \sum(line_item.amount) ≈ subtotal\.
3. **Total Validation**: Checks if \subtotal + tax ≈ total\.

## Decimal Strategy
All calculations use Python's \Decimal\ objects. Floating-point arithmetic (\loat\) is completely avoided to prevent subtle precision losses when dealing with monetary values.

## Tolerance Strategy
A centralized tolerance of \Decimal("0.01")\ is used for all validations.
**Why?** Invoices frequently have fractional currency rounding discrepancies (e.g., tax calculated line-by-line vs. calculated on the subtotal) or visual truncations. Instead of aggressively failing invoices that are off by a single cent, differences within 0.01 are accepted as valid.

## Missing-Data Behavior
The validator explicitly distinguishes between **INVALID** and **NOT VERIFIABLE**.
- If there are no line items, the validator generates a warning instead of falsely failing the subtotal check.
- If tax is missing but subtotal and total are present, the validator does **not** assume tax is zero. It generates a warning indicating that the total cannot be fully verified.
- The service does not guess missing values.

## No-Auto-Correction Principle
If an invoice lists a subtotal of 100, tax of 10, and a total of 150, the validator flags this as an error. It strictly forbids modifying the \	otal\ to 110. The integrity of the original parsed document is maintained, and discrepancies are elevated for human review.

## Limitations
- **Currency Conversion**: The validator assumes all values are in the same currency (the invoice's stated currency). It does not perform cross-currency conversions.
- **External Data**: It only verifies internal mathematical consistency, not whether the tax rate matches legal regional guidelines.
