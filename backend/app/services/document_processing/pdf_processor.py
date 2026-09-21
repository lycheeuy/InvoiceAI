import logging
import pdfplumber
from pathlib import Path
from typing import Union
from .base import DocumentProcessor
from .schemas import DocumentProcessingResult, ProcessingMethod, DocumentType

# Gunakan logger bawaan FastAPI/project jika nanti diperlukan
logger = logging.getLogger(__name__)

class PdfTextProcessor(DocumentProcessor):
    def process(self, file_path: Union[Path, str]) -> DocumentProcessingResult:
        file_path = Path(file_path)
        extracted_text_parts = []
        page_count = 0
        warnings = []
        errors = []

        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        # Mempertahankan page boundaries
                        extracted_text_parts.append(f"--- Page {i + 1} ---\n{text}")
                    else:
                        warnings.append(f"Page {i + 1} berisi teks kosong atau tidak dapat diekstrak.")
        except Exception as e:
            logger.error(f"Gagal memproses PDF {file_path}: {e}")
            errors.append(str(e))
            return DocumentProcessingResult(
                processing_method=ProcessingMethod.PDFPLUMBER,
                document_type=DocumentType.DIGITAL_PDF,
                page_count=page_count,
                errors=errors,
                warnings=warnings
            )

        extracted_text = "\n\n".join(extracted_text_parts) if extracted_text_parts else ""

        if not extracted_text and not errors:
            warnings.append("Dokumen tidak memiliki teks sama sekali di seluruh halaman.")

        return DocumentProcessingResult(
            processing_method=ProcessingMethod.PDFPLUMBER,
            document_type=DocumentType.DIGITAL_PDF,
            extracted_text=extracted_text,
            page_count=page_count,
            warnings=warnings,
            errors=errors
        )