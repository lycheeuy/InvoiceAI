import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import date
from pydantic import ValidationError

from backend.app.services.invoice_extraction_service import InvoiceExtractionService, InvoiceExtractionError
from backend.app.schemas.invoice import InvoiceSchema

@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    return client

def test_missing_api_key(monkeypatch):
    monkeypatch.setattr('backend.app.services.invoice_extraction_service.settings.GEMINI_API_KEY', None)
    service = InvoiceExtractionService(client=None)
    with pytest.raises(InvoiceExtractionError, match="GEMINI_API_KEY tidak dikonfigurasi."):
        service.extract_invoice("Some text")

def test_successful_structured_invoice_extraction(mock_genai_client):
    # Mock complete response
    mock_response = MagicMock()
    mock_response.text = '''
    {
      "invoice_number": "INV-100",
      "vendor": {
        "name": "Vendor A",
        "address": "123 St",
        "tax_id": "TAX123"
      },
      "invoice_date": "2026-09-21",
      "due_date": "2026-10-21",
      "currency": "USD",
      "subtotal": "100.50",
      "tax": "10.05",
      "total": "110.55",
      "line_items": [
        {
          "description": "Item 1",
          "quantity": "2.5",
          "unit_price": "40.20",
          "amount": "100.50"
        }
      ]
    }
    '''
    mock_genai_client.models.generate_content.return_value = mock_response
    
    service = InvoiceExtractionService(client=mock_genai_client)
    invoice = service.extract_invoice("Document text")
    
    # Verify Complete InvoiceSchema returned correctly
    assert isinstance(invoice, InvoiceSchema)
    assert invoice.invoice_number == "INV-100"
    
    # Verify Decimal monetary values are preserved
    assert invoice.total == Decimal('110.55')
    assert invoice.subtotal == Decimal('100.50')
    assert isinstance(invoice.total, Decimal)
    
    # Verify Line items are parsed correctly
    assert len(invoice.line_items) == 1
    assert invoice.line_items[0].description == "Item 1"
    assert invoice.line_items[0].quantity == Decimal('2.5')
    assert invoice.line_items[0].amount == Decimal('100.50')

    # Date handling
    assert invoice.invoice_date == date(2026, 9, 21)

def test_optional_missing_fields_become_none(mock_genai_client):
    mock_response = MagicMock()
    mock_response.text = '''
    {
      "invoice_number": "INV-101"
    }
    '''
    mock_genai_client.models.generate_content.return_value = mock_response
    
    service = InvoiceExtractionService(client=mock_genai_client)
    invoice = service.extract_invoice("Document text")
    
    assert invoice.invoice_number == "INV-101"
    assert invoice.vendor is None
    assert invoice.due_date is None
    assert invoice.tax is None
    assert invoice.line_items == []

def test_gemini_api_failure(mock_genai_client):
    mock_genai_client.models.generate_content.side_effect = Exception("API Outage")
    service = InvoiceExtractionService(client=mock_genai_client)
    
    with pytest.raises(InvoiceExtractionError, match="Gagal melakukan ekstraksi: API Outage"):
        service.extract_invoice("Document text")

def test_empty_gemini_response(mock_genai_client):
    mock_response = MagicMock()
    mock_response.text = ""
    mock_genai_client.models.generate_content.return_value = mock_response
    
    service = InvoiceExtractionService(client=mock_genai_client)
    with pytest.raises(InvoiceExtractionError, match="Gemini API mengembalikan respons kosong."):
        service.extract_invoice("Document text")

def test_malformed_structured_response(mock_genai_client):
    mock_response = MagicMock()
    mock_response.text = "{ malformed json "
    mock_genai_client.models.generate_content.return_value = mock_response
    
    service = InvoiceExtractionService(client=mock_genai_client)
    with pytest.raises(InvoiceExtractionError, match="Data yang diekstrak tidak valid"):
        service.extract_invoice("Document text")

def test_pydantic_validation_failure(mock_genai_client):
    mock_response = MagicMock()
    # Provide a string where a list is expected for line_items
    mock_response.text = '''
    {
      "invoice_number": "INV-100",
      "line_items": "not a list"
    }
    '''
    mock_genai_client.models.generate_content.return_value = mock_response
    
    service = InvoiceExtractionService(client=mock_genai_client)
    with pytest.raises(InvoiceExtractionError, match="Data yang diekstrak tidak valid"):
        service.extract_invoice("Document text")

def test_negative_value_pydantic_validation_failure(mock_genai_client):
    mock_response = MagicMock()
    mock_response.text = '''
    {
      "invoice_number": "INV-100",
      "total": "-10.00"
    }
    '''
    mock_genai_client.models.generate_content.return_value = mock_response
    
    service = InvoiceExtractionService(client=mock_genai_client)
    with pytest.raises(InvoiceExtractionError, match="Data yang diekstrak tidak valid"):
        service.extract_invoice("Document text")
