from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ProcessingMethod(str, Enum):
    PDFPLUMBER = "pdfplumber"
    GEMINI = "gemini"

class DocumentType(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"

class DocumentProcessingResult(BaseModel):
    processing_method: ProcessingMethod
    document_type: DocumentType
    extracted_text: Optional[str] = None
    page_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)