import io
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.api.v1.endpoints import invoices as invoices_endpoint
from backend.app.services.document import DocumentStorageService
from backend.app.services.invoice_service import InvoiceService

# In-memory SQLite engine for fast, isolated, zero-dependency testing
TEST_SQLITE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create database tables once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a clean transactional database session per test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def temp_storage(tmp_path: Path) -> Generator[Path, None, None]:
    """Provides a temporary, isolated storage directory for file upload tests."""
    storage_dir = tmp_path / "storage" / "invoices"
    storage_dir.mkdir(parents=True, exist_ok=True)
    yield storage_dir
    if storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)


@pytest.fixture
def client(db_session: Session, temp_storage: Path) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden database session and temporary storage service."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override FastAPI dependencies and services for test isolation
    app.dependency_overrides[get_db] = override_get_db

    # Inject test-scoped DocumentStorageService pointing to temp directory
    test_storage_service = DocumentStorageService(
        storage_dir=str(temp_storage),
        max_file_size=settings.MAX_UPLOAD_SIZE,
        allowed_extensions=settings.allowed_extensions_set,
    )
    invoices_endpoint.invoice_service = InvoiceService(storage_service=test_storage_service)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# Helper binary fixtures
@pytest.fixture
def valid_pdf_bytes() -> bytes:
    """Valid PDF header and minimal content."""
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture
def valid_png_bytes() -> bytes:
    """Valid PNG magic signature and minimal chunk."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Valid JPEG magic signature."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb"
