import logging
from pathlib import Path
from typing import Union
from google import genai

from backend.app.core.config import settings
from .base import DocumentProcessor
from .schemas import DocumentProcessingResult, ProcessingMethod, DocumentType

logger = logging.getLogger(__name__)

class GeminiDocumentProcessor(DocumentProcessor):
    def process(self, file_path: Union[Path, str]) -> DocumentProcessingResult:
        file_path = Path(file_path)
        
        errors = []
        warnings = []
        
        if not file_path.exists():
            errors.append(f"File tidak ditemukan: {file_path}")
            return DocumentProcessingResult(
                processing_method=ProcessingMethod.GEMINI,
                document_type=DocumentType.IMAGE,
                errors=errors
            )
            
        ext = file_path.suffix.lower()
        if ext not in [".png", ".jpg", ".jpeg", ".pdf"]:
            errors.append(f"Format file tidak didukung oleh Gemini: {ext}")
            return DocumentProcessingResult(
                processing_method=ProcessingMethod.GEMINI,
                document_type=DocumentType.IMAGE, 
                errors=errors
            )
            
        doc_type = DocumentType.SCANNED_PDF if ext == ".pdf" else DocumentType.IMAGE
        
        if not settings.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY tidak dikonfigurasi.")
            return DocumentProcessingResult(
                processing_method=ProcessingMethod.GEMINI,
                document_type=doc_type,
                errors=errors
            )
            
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            prompt = (
                "Extract all readable text from this document. "
                "Preserve the original wording and useful structure as much as possible. "
                "Do not summarize. Do not infer or invent missing content. "
                "Return only the extracted document text."
            )
            
            uploaded_file = client.files.upload(file=str(file_path))
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[uploaded_file, prompt]
            )
            
            extracted_text = response.text
            
            if not extracted_text:
                warnings.append("Gemini mengembalikan respons kosong.")
                extracted_text = ""
                
            return DocumentProcessingResult(
                processing_method=ProcessingMethod.GEMINI,
                document_type=doc_type,
                extracted_text=extracted_text,
                page_count=0,
                warnings=warnings,
                errors=errors
            )
        except Exception as e:
            logger.error(f"Gemini API error saat memproses {file_path}: {e}")
            errors.append(f"Gemini API error: {str(e)}")
            return DocumentProcessingResult(
                processing_method=ProcessingMethod.GEMINI,
                document_type=doc_type,
                errors=errors
            )
