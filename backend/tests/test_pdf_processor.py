import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from backend.app.services.document_processing.pdf_processor import PdfTextProcessor
from backend.app.services.document_processing.schemas import DocumentProcessingResult, ProcessingMethod, DocumentType

@pytest.fixture
def pdf_processor():
    return PdfTextProcessor()

def create_mock_pdf(pages_text):
    mock_pdf = MagicMock()
    mock_pages = []
    for text in pages_text:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = text
        mock_pages.append(mock_page)
    mock_pdf.pages = mock_pages
    return mock_pdf

@patch('backend.app.services.document_processing.pdf_processor.pdfplumber.open')
def test_successful_digital_pdf(mock_pdfplumber_open, pdf_processor):
    mock_pdfplumber_open.return_value.__enter__.return_value = create_mock_pdf([
        "Invoice No: 12345",
        "Total: $100.00"
    ])

    result = pdf_processor.process(Path("dummy.pdf"))

    assert result.processing_method == ProcessingMethod.PDFPLUMBER
    assert result.document_type == DocumentType.DIGITAL_PDF
    assert result.page_count == 2
    assert "--- Page 1 ---" in result.extracted_text
    assert "Invoice No: 12345" in result.extracted_text
    assert "--- Page 2 ---" in result.extracted_text
    assert "Total: $100.00" in result.extracted_text
    assert not result.errors
    assert not result.warnings

@patch('backend.app.services.document_processing.pdf_processor.pdfplumber.open')
def test_empty_or_no_text_pdf(mock_pdfplumber_open, pdf_processor):
    mock_pdfplumber_open.return_value.__enter__.return_value = create_mock_pdf([
        "",
        "   \n  "
    ])

    result = pdf_processor.process(Path("dummy.pdf"))

    assert result.page_count == 2
    assert result.extracted_text == ""
    assert not result.errors
    assert len(result.warnings) == 3 # 2 warnings for empty pages, 1 for whole doc

@patch('backend.app.services.document_processing.pdf_processor.pdfplumber.open')
def test_missing_pdf_file(mock_pdfplumber_open, pdf_processor):
    mock_pdfplumber_open.side_effect = FileNotFoundError("File not found")

    result = pdf_processor.process(Path("missing.pdf"))

    assert result.processing_method == ProcessingMethod.PDFPLUMBER
    assert result.document_type == DocumentType.DIGITAL_PDF
    assert result.page_count == 0
    assert result.extracted_text is None
    assert len(result.errors) == 1
    assert "File not found" in result.errors[0]

@patch('backend.app.services.document_processing.pdf_processor.pdfplumber.open')
def test_corrupt_pdf_file(mock_pdfplumber_open, pdf_processor):
    mock_pdfplumber_open.side_effect = Exception("Corrupted PDF")

    result = pdf_processor.process(Path("corrupted.pdf"))

    assert result.page_count == 0
    assert result.extracted_text is None
    assert len(result.errors) == 1
    assert "Corrupted PDF" in result.errors[0]
