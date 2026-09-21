import logging
import sys
from backend.app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configures structured console logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("invoiceai")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
