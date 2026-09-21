import pytest
from unittest.mock import MagicMock
from pathlib import Path

from backend.app.services.document_processing.router import DocumentRouter
from backend.app.services.document_processing.base import DocumentProcessor
from backend.app.services.document_processing.schemas import DocumentProcessingResult, ProcessingMethod, DocumentType

@pytest.fixture
def mock_gemini():
    return MagicMock(spec=DocumentProcessor)

@pytest.fixture
def mock_pdf_processor():
    return MagicMock(spec=DocumentProcessor)

@pytest.fixture
def router(mock_gemini, mock_pdf_processor):
    r = DocumentRouter(gemini_processor=mock_gemini)
    r.pdf_text_processor = mock_pdf_processor
    return r

def test_router_png(router, mock_gemini):
    mock_gemini.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.GEMINI,
        document_type=DocumentType.IMAGE,
    )
    result = router.process(Path("test.png"))
    mock_gemini.process.assert_called_once_with(Path("test.png"))
    assert result.processing_method == ProcessingMethod.GEMINI

def test_router_jpg(router, mock_gemini):
    mock_gemini.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.GEMINI,
        document_type=DocumentType.IMAGE,
    )
    result = router.process(Path("test.jpg"))
    mock_gemini.process.assert_called_once_with(Path("test.jpg"))
    assert result.processing_method == ProcessingMethod.GEMINI

def test_router_jpeg(router, mock_gemini):
    mock_gemini.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.GEMINI,
        document_type=DocumentType.IMAGE,
    )
    result = router.process(Path("test.jpeg"))
    mock_gemini.process.assert_called_once_with(Path("test.jpeg"))
    assert result.processing_method == ProcessingMethod.GEMINI

def test_router_digital_pdf(router, mock_pdf_processor, mock_gemini):
    # PDF with >= 100 meaningful chars
    text = "A" * 100
    mock_pdf_processor.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        extracted_text=text
    )
    result = router.process(Path("test.pdf"))
    mock_pdf_processor.process.assert_called_once_with(Path("test.pdf"))
    mock_gemini.process.assert_not_called()
    assert result.processing_method == ProcessingMethod.PDFPLUMBER
    assert result.document_type == DocumentType.DIGITAL_PDF

def test_router_scanned_pdf(router, mock_pdf_processor, mock_gemini):
    # PDF with < 100 meaningful chars
    text = "A" * 99
    mock_pdf_processor.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        extracted_text=text
    )
    mock_gemini.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.GEMINI,
        document_type=DocumentType.SCANNED_PDF,
    )
    result = router.process(Path("test.pdf"))
    mock_pdf_processor.process.assert_called_once_with(Path("test.pdf"))
    mock_gemini.process.assert_called_once_with(Path("test.pdf"))
    assert result.processing_method == ProcessingMethod.GEMINI
    assert result.document_type == DocumentType.SCANNED_PDF

def test_router_unsupported_extension(router):
    with pytest.raises(ValueError, match="Tipe file tidak didukung: .txt"):
        router.process(Path("test.txt"))

def test_router_no_gemini_for_image():
    r = DocumentRouter(gemini_processor=None)
    with pytest.raises(ValueError, match="wajib di-inject"):
        r.process(Path("test.png"))

def test_router_no_gemini_for_scanned_pdf(mock_pdf_processor):
    r = DocumentRouter(gemini_processor=None)
    r.pdf_text_processor = mock_pdf_processor
    mock_pdf_processor.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        extracted_text="short"
    )
    with pytest.raises(ValueError, match="wajib di-inject"):
        r.process(Path("test.pdf"))

def test_router_pdf_extraction_error(router, mock_pdf_processor, mock_gemini):
    mock_pdf_processor.process.return_value = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        errors=["File not found"]
    )
    result = router.process(Path("test.pdf"))
    mock_pdf_processor.process.assert_called_once_with(Path("test.pdf"))
    mock_gemini.process.assert_not_called()
    assert result.processing_method == ProcessingMethod.PDFPLUMBER
    assert "File not found" in result.errors
