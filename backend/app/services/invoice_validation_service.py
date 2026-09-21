import logging
from decimal import Decimal
from typing import List
from pydantic import BaseModel

from backend.app.schemas.invoice import InvoiceSchema

logger = logging.getLogger(__name__)

class FinancialValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class InvoiceValidationService:
    # Tolerance of 0.01 for standard currency rounding differences.
    # This accounts for invoices that might calculate tax line-by-line vs on the subtotal,
    # or have minor floating-point-like visual truncations.
    TOLERANCE = Decimal("0.01")
    
    @classmethod
    def validate_invoice(cls, invoice: InvoiceSchema) -> FinancialValidationResult:
        errors = []
        warnings = []
        
        # 1. Line Item Validation
        if invoice.line_items:
            for idx, item in enumerate(invoice.line_items):
                if item.quantity is not None and item.unit_price is not None and item.amount is not None:
                    calculated_amount = item.quantity * item.unit_price
                    if abs(calculated_amount - item.amount) > cls.TOLERANCE:
                        errors.append(f"Line item {idx + 1} amount ({item.amount}) does not match quantity ({item.quantity}) × unit_price ({item.unit_price}).")
                else:
                    warnings.append(f"Line item {idx + 1} is missing quantity, unit_price, or amount; skipping line item arithmetic validation.")
        else:
            warnings.append("Missing line items; subtotal cannot be reconstructed from line items.")
            
        # 2. Subtotal Validation
        if invoice.subtotal is not None:
            if invoice.line_items:
                # Only check subtotal if ALL line items have an amount
                if all(item.amount is not None for item in invoice.line_items):
                    calculated_subtotal = sum((item.amount for item in invoice.line_items), Decimal('0'))
                    if abs(calculated_subtotal - invoice.subtotal) > cls.TOLERANCE:
                        errors.append(f"Subtotal ({invoice.subtotal}) does not match the sum of line item amounts ({calculated_subtotal}).")
                else:
                    warnings.append("Some line items are missing amounts; skipping subtotal arithmetic validation.")
        else:
            warnings.append("Subtotal is missing; cannot verify sum of line items.")
            
        # 3. Total Validation
        if invoice.total is not None:
            if invoice.subtotal is not None and invoice.tax is not None:
                calculated_total = invoice.subtotal + invoice.tax
                if abs(calculated_total - invoice.total) > cls.TOLERANCE:
                    errors.append(f"Total ({invoice.total}) does not match subtotal ({invoice.subtotal}) + tax ({invoice.tax}).")
            else:
                missing = []
                if invoice.subtotal is None: missing.append("subtotal")
                if invoice.tax is None: missing.append("tax")
                warnings.append(f"Cannot verify total because {', '.join(missing)} is missing.")
        else:
            warnings.append("Total is missing; cannot verify subtotal + tax.")
            
        return FinancialValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
