import pytest
from pydantic import ValidationError

from backend.app.services.document_processing.schemas import (
    DocumentProcessingResult,
    ProcessingMethod,
    DocumentType
)

def test_processing_method_values():
    assert ProcessingMethod.PDFPLUMBER == "pdfplumber"
    assert ProcessingMethod.GEMINI == "gemini"

def test_document_type_values():
    assert DocumentType.DIGITAL_PDF == "digital_pdf"
    assert DocumentType.SCANNED_PDF == "scanned_pdf"
    assert DocumentType.IMAGE == "image"

def test_document_processing_result_valid():
    result = DocumentProcessingResult(
        processing_method=ProcessingMethod.PDFPLUMBER,
        document_type=DocumentType.DIGITAL_PDF,
        extracted_text="Hello",
        page_count=1,
        warnings=["A warning"],
        errors=[]
    )
    assert result.processing_method == ProcessingMethod.PDFPLUMBER
    assert result.document_type == DocumentType.DIGITAL_PDF
    assert result.extracted_text == "Hello"
    assert result.page_count == 1
    assert result.warnings == ["A warning"]
    assert result.errors == []

def test_document_processing_result_invalid_processing_method():
    with pytest.raises(ValidationError):
        DocumentProcessingResult(
            processing_method="invalid_method",
            document_type=DocumentType.DIGITAL_PDF
        )

def test_document_processing_result_invalid_document_type():
    with pytest.raises(ValidationError):
        DocumentProcessingResult(
            processing_method=ProcessingMethod.PDFPLUMBER,
            document_type="invalid_type"
        )
