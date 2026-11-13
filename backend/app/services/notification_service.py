
from decimal import Decimal
from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.invoice import Invoice


class NotificationService:
    """Sends invoice event notifications to n8n."""

    EVENT_TYPES = {
        "PROCESSED": "invoice.processed",
        "FAILED": "invoice.failed",
        "NEEDS_REVIEW": "invoice.needs_review",
    }

    @staticmethod
    def notify_invoice_event(invoice: Invoice) -> bool:
        """Send an invoice event to n8n without interrupting invoice processing."""

        if not settings.N8N_WEBHOOK_URL or not settings.N8N_WEBHOOK_TOKEN:
            logger.debug("n8n notification skipped: webhook is not configured.")
            return False

        status = getattr(invoice.status, "value", invoice.status)
        event_type = NotificationService.EVENT_TYPES.get(str(status))

        if not event_type:
            logger.debug(
                "n8n notification skipped for invoice %s: unsupported status %s",
                invoice.id,
                invoice.status,
            )
            return False

        total: float | None = (
            float(invoice.total)
            if isinstance(invoice.total, Decimal)
            else invoice.total
        )

        payload: dict[str, Any] = {
            "event_type": event_type,
            "data": {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "vendor": invoice.vendor_name,
                "total": total,
                "status": str(status),
                "review_reason": invoice.review_reason,
            },
        }

        headers = {
            "X-InvoiceAI-Token": settings.N8N_WEBHOOK_TOKEN,
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                timeout=settings.N8N_WEBHOOK_TIMEOUT
            ) as client:
                response = client.post(
                    settings.N8N_WEBHOOK_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

            logger.info(
                "n8n notification sent: event=%s invoice_id=%s",
                event_type,
                invoice.id,
            )
            return True

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "n8n notification rejected: status=%s invoice_id=%s",
                exc.response.status_code,
                invoice.id,
            )
        except httpx.RequestError as exc:
            logger.warning(
                "n8n notification request failed: error=%s invoice_id=%s",
                type(exc).__name__,
                invoice.id,
            )
        except Exception:
            logger.exception(
                "Unexpected n8n notification error for invoice_id=%s",
                invoice.id,
            )

        return False
