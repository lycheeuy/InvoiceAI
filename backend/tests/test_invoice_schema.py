from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError
from backend.app.schemas.invoice import InvoiceSchema, Vendor, LineItem

def test_valid_complete_invoice():
    vendor = Vendor(name="Acme Corp", address="123 Road", tax_id="TAX-123")
    line_item = LineItem(description="Widget", quantity=Decimal('2.5'), unit_price=Decimal('10.00'), amount=Decimal('25.00'))
    invoice = InvoiceSchema(
        invoice_number="INV-001",
        vendor=vendor,
        invoice_date=date(2026, 9, 21),
        due_date=date(2026, 10, 21),
        currency="USD",
        subtotal=Decimal('25.00'),
        tax=Decimal('2.50'),
        total=Decimal('27.50'),
        line_items=[line_item]
    )
    assert invoice.invoice_number == "INV-001"
    assert invoice.total == Decimal('27.50')

def test_valid_invoice_optional_fields_missing():
    invoice = InvoiceSchema(invoice_number="INV-002")
    assert invoice.vendor is None
    assert invoice.tax is None
    assert invoice.line_items == []

def test_valid_decimal_monetary_values():
    invoice = InvoiceSchema(subtotal=Decimal('100.50'), tax=Decimal('10.05'), total=Decimal('110.55'))
    assert isinstance(invoice.subtotal, Decimal)
    assert invoice.total == Decimal('110.55')

def test_fractional_quantity():
    line_item = LineItem(description="Labor", quantity=Decimal('1.5'), unit_price=Decimal('100'))
    assert line_item.quantity == Decimal('1.5')

def test_invalid_date():
    with pytest.raises(ValidationError):
        InvoiceSchema(invoice_date="not-a-date")

def test_negative_quantity_rejected():
    with pytest.raises(ValidationError):
        LineItem(quantity=Decimal('-1'))

def test_negative_monetary_values_rejected():
    with pytest.raises(ValidationError):
        InvoiceSchema(total=Decimal('-10.00'))
    with pytest.raises(ValidationError):
        InvoiceSchema(subtotal=Decimal('-5.00'))
    with pytest.raises(ValidationError):
        InvoiceSchema(tax=Decimal('-0.50'))
    with pytest.raises(ValidationError):
        LineItem(unit_price=Decimal('-10.00'))
    with pytest.raises(ValidationError):
        LineItem(amount=Decimal('-10.00'))

def test_missing_fields_default_to_none():
    invoice = InvoiceSchema.model_validate({})
    assert invoice.invoice_number is None
    assert invoice.invoice_date is None
    assert invoice.vendor is None

def test_json_serialization_decimal_as_string():
    invoice = InvoiceSchema(total=Decimal('100.50'))
    json_str = invoice.model_dump_json()
    assert '"total":"100.50"' in json_str
    assert '100.5' not in json_str.replace('"100.50"', '') # Ensure it wasn't converted to float

def test_nested_line_items_validate_correctly():
    data = {
        "invoice_number": "INV-123",
        "line_items": [
            {"description": "Item 1", "quantity": "2", "unit_price": "10", "amount": "20"},
            {"description": "Item 2", "quantity": "-1"} # Invalid quantity
        ]
    }
    with pytest.raises(ValidationError) as exc:
        InvoiceSchema.model_validate(data)
    assert "quantity" in str(exc.value)

