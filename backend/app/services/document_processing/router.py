import logging
from pathlib import Path
from typing import Union, Optional
from .base import DocumentProcessor
from .pdf_processor import PdfTextProcessor
from .schemas import DocumentProcessingResult, DocumentType

logger = logging.getLogger(__name__)

class DocumentRouter:
    def __init__(self, gemini_processor: Optional[DocumentProcessor] = None):
        """
        gemini_processor di-inject via Dependency Injection.
        Hal ini memungkinkan kita me-mock GeminiProcessor di testing atau 
        menunda inisialisasinya (karena kita belum mengimplementasikan Gemini).
        """
        self.pdf_text_processor = PdfTextProcessor()
        self.gemini_processor = gemini_processor
        self.meaningful_char_threshold = 100

    def _count_alphanumeric(self, text: str) -> int:
        if not text:
            return 0
        return sum(c.isalnum() for c in text)

    def process(self, file_path: Union[Path, str]) -> DocumentProcessingResult:
        file_path = Path(file_path)
        ext = file_path.suffix.lower()

        if ext in [".png", ".jpg", ".jpeg"]:
            if not self.gemini_processor:
                raise ValueError("Gemini processor wajib di-inject untuk file gambar (PNG/JPG/JPEG).")
            logger.info(f"Routing {file_path.name} (Image) ke Gemini processor.")
            return self.gemini_processor.process(file_path)

        elif ext == ".pdf":
            # 1. Ekstrak text secara default dengan pdfplumber
            logger.info(f"Memproses {file_path.name} dengan PdfTextProcessor terlebih dahulu.")
            pdf_result = self.pdf_text_processor.process(file_path)

            if pdf_result.errors:
                logger.warning(f"Terjadi error ekstraksi PDF di {file_path.name}. Returning error result.")
                return pdf_result

            # 2. Hitung jumlah karakter alfanumerik sebagai Heuristic MVP
            char_count = self._count_alphanumeric(pdf_result.extracted_text)
            
            # 3. Keputusan Routing
            if char_count >= self.meaningful_char_threshold:
                logger.info(f"Digital PDF terdeteksi ({char_count} chars >= {self.meaningful_char_threshold}).")
                return pdf_result
            else:
                logger.info(f"Scanned PDF/Empty PDF terdeteksi ({char_count} chars < {self.meaningful_char_threshold}). Routing ke Gemini.")
                if not self.gemini_processor:
                    raise ValueError("Gemini processor wajib di-inject untuk scanned/image-based PDFs.")
                
                gemini_result = self.gemini_processor.process(file_path)
                # Secara eksplisit pastikan dokumen ditandai sebagai SCANNED_PDF
                gemini_result.document_type = DocumentType.SCANNED_PDF
                return gemini_result

        else:
            raise ValueError(f"Tipe file tidak didukung: {ext}")