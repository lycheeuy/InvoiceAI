import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.app.services.document_processing.gemini_processor import GeminiDocumentProcessor
from backend.app.services.document_processing.schemas import ProcessingMethod, DocumentType
from backend.app.core.config import settings

@pytest.fixture
def processor():
    return GeminiDocumentProcessor()

@pytest.fixture
def mock_genai_client():
    with patch("backend.app.services.document_processing.gemini_processor.genai.Client") as mock_client:
        yield mock_client

@pytest.fixture
def valid_png_path(tmp_path):
    p = tmp_path / "test.png"
    p.write_bytes(b"fake png data")
    return p

@pytest.fixture
def valid_pdf_path(tmp_path):
    p = tmp_path / "test.pdf"
    p.write_bytes(b"fake pdf data")
    return p

def test_missing_api_key(processor, valid_png_path, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    
    result = processor.process(valid_png_path)
    
    assert result.processing_method == ProcessingMethod.GEMINI
    assert result.document_type == DocumentType.IMAGE
    assert len(result.errors) == 1
    assert "GEMINI_API_KEY tidak dikonfigurasi" in result.errors[0]

def test_unsupported_extension(processor, tmp_path):
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("Hello")
    
    result = processor.process(txt_path)
    
    assert len(result.errors) == 1
    assert "Format file tidak didukung" in result.errors[0]

def test_file_not_found(processor):
    result = processor.process("nonexistent.pdf")
    
    assert len(result.errors) == 1
    assert "File tidak ditemukan" in result.errors[0]

def test_successful_image_processing(processor, mock_genai_client, valid_png_path, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    
    mock_upload = MagicMock()
    mock_instance.files.upload.return_value = mock_upload
    
    mock_response = MagicMock()
    mock_response.text = "Extracted Image Text"
    mock_instance.models.generate_content.return_value = mock_response
    
    result = processor.process(valid_png_path)
    
    assert result.processing_method == ProcessingMethod.GEMINI
    assert result.document_type == DocumentType.IMAGE
    assert result.extracted_text == "Extracted Image Text"
    assert len(result.errors) == 0

def test_successful_pdf_processing(processor, mock_genai_client, valid_pdf_path, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    
    mock_upload = MagicMock()
    mock_instance.files.upload.return_value = mock_upload
    
    mock_response = MagicMock()
    mock_response.text = "Extracted PDF Text"
    mock_instance.models.generate_content.return_value = mock_response
    
    result = processor.process(valid_pdf_path)
    
    assert result.processing_method == ProcessingMethod.GEMINI
    assert result.document_type == DocumentType.SCANNED_PDF
    assert result.extracted_text == "Extracted PDF Text"
    assert len(result.errors) == 0

def test_gemini_api_failure(processor, mock_genai_client, valid_png_path, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    
    mock_instance.files.upload.side_effect = Exception("API Down")
    
    result = processor.process(valid_png_path)
    
    assert len(result.errors) == 1
    assert "Gemini API error: API Down" in result.errors[0]

def test_empty_gemini_response(processor, mock_genai_client, valid_png_path, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key")
    
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    
    mock_upload = MagicMock()
    mock_instance.files.upload.return_value = mock_upload
    
    mock_response = MagicMock()
    mock_response.text = "" # empty
    mock_instance.models.generate_content.return_value = mock_response
    
    result = processor.process(valid_png_path)
    
    assert result.extracted_text == ""
    assert len(result.warnings) == 1
    assert "Gemini mengembalikan respons kosong" in result.warnings[0]
