import logging
from typing import Optional
from google import genai
from google.genai import types
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.schemas.invoice import InvoiceSchema

logger = logging.getLogger(__name__)

class InvoiceExtractionError(Exception):
    pass

class InvoiceExtractionService:
    def __init__(self, client: Optional[genai.Client] = None):
        if client:
            self.client = client
        elif settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None

    def extract_invoice(self, document_text: str) -> InvoiceSchema:
        if not self.client:
            raise InvoiceExtractionError("GEMINI_API_KEY tidak dikonfigurasi.")

        prompt = (
            "You are an expert invoice data extractor. "
            "Extract the following information from the provided document text into structured JSON. "
            "IMPORTANT RULES: "
            "1. Extract ONLY information explicitly supported by the document text. "
            "2. DO NOT invent, infer, or hallucinate missing values. "
            "3. If a piece of information is missing or unavailable, use null. "
            "4. Preserve the original invoice wording where appropriate. "
            "5. Identify the vendor's name, address, and tax ID. "
            "6. Identify the invoice number, invoice date, and due date. "
            "7. Identify the currency, subtotal, tax, and total. "
            "8. Extract line items when present (description, quantity, unit price, amount). "
            "9. DO NOT calculate missing values or fix inconsistent totals. You are a semantic parser, not a calculator.\n\n"
            "Document Text:\n"
            f"{document_text}"
        )

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InvoiceSchema,
                ),
            )
            
            if not response.text:
                raise InvoiceExtractionError("Gemini API mengembalikan respons kosong.")

            try:
                invoice_data = InvoiceSchema.model_validate_json(response.text)
                return invoice_data
            except ValidationError as ve:
                logger.error(f"Pydantic validation error: {ve}")
                raise InvoiceExtractionError(f"Data yang diekstrak tidak valid: {ve}")

        except InvoiceExtractionError:
            raise
        except Exception as e:
            logger.error(f"Gemini API extraction error: {e}")
            raise InvoiceExtractionError(f"Gagal melakukan ekstraksi: {str(e)}")
