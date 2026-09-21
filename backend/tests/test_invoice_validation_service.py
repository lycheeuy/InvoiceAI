import pytest
from decimal import Decimal

from backend.app.schemas.invoice import InvoiceSchema, LineItem
from backend.app.services.invoice_validation_service import InvoiceValidationService

def test_completely_valid_invoice():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.00"),
        line_items=[
            LineItem(quantity=Decimal("2"), unit_price=Decimal("25.00"), amount=Decimal("50.00")),
            LineItem(quantity=Decimal("1"), unit_price=Decimal("50.00"), amount=Decimal("50.00")),
        ]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is True
    assert len(result.errors) == 0

def test_valid_invoice_no_line_items():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.00"),
        line_items=[]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert any("Missing line items" in w for w in result.warnings)

def test_line_item_arithmetic_invalid():
    invoice = InvoiceSchema(
        subtotal=Decimal("60.00"),
        tax=Decimal("0.00"),
        total=Decimal("60.00"),
        line_items=[
            LineItem(quantity=Decimal("2"), unit_price=Decimal("25.00"), amount=Decimal("60.00")),
        ]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is False
    assert any("does not match quantity" in e for e in result.errors)

def test_subtotal_mismatch():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.00"),
        line_items=[
            LineItem(quantity=Decimal("2"), unit_price=Decimal("25.00"), amount=Decimal("50.00")),
        ]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is False
    assert any("does not match the sum of line item amounts" in e for e in result.errors)

def test_total_mismatch():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("100.00"),
        line_items=[]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is False
    assert any("Total (100.00) does not match subtotal" in e for e in result.errors)

def test_missing_tax_not_falsely_invalid():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        total=Decimal("100.00"),
        line_items=[]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert any("Cannot verify total because tax is missing" in w for w in result.warnings)

def test_missing_subtotal_behavior():
    invoice = InvoiceSchema(
        tax=Decimal("10.00"),
        total=Decimal("110.00"),
        line_items=[]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is True
    assert any("Subtotal is missing; cannot verify sum of line items" in w for w in result.warnings)
    assert any("Cannot verify total because subtotal is missing" in w for w in result.warnings)

def test_decimal_precision_and_tolerance_valid():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.01"),
        line_items=[]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is True

def test_decimal_precision_and_tolerance_invalid():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("110.02"),
        line_items=[]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is False
    assert any("Total (110.02) does not match subtotal (100.00) + tax (10.00)" in e for e in result.errors)

def test_multiple_validation_errors():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("150.00"),
        line_items=[
            LineItem(quantity=Decimal("2"), unit_price=Decimal("20.00"), amount=Decimal("50.00"))
        ]
    )
    result = InvoiceValidationService.validate_invoice(invoice)
    assert result.is_valid is False
    assert len(result.errors) == 3

def test_validator_does_not_mutate():
    invoice = InvoiceSchema(
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("150.00"),
        line_items=[]
    )
    original_total = invoice.total
    InvoiceValidationService.validate_invoice(invoice)
    assert invoice.total == original_total
