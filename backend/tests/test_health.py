import logging
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, ENV_FILE, settings
from backend.app.db.session import get_db
from backend.app.main import app


def test_root_health_endpoint(client: TestClient):
    """Tests GET /health returns 200 and healthy database status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_api_v1_health_endpoint(client: TestClient):
    """Tests GET /api/v1/health returns 200 and healthy database status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_settings_loads_backend_env_from_project_root():
    """Verify Settings loads configuration from backend/.env regardless of CWD."""
    assert ENV_FILE.exists()
    assert ENV_FILE.name == ".env"
    fresh_settings = Settings()
    assert fresh_settings.DATABASE_URL == settings.DATABASE_URL
    assert "postgres:postgres@" not in fresh_settings.DATABASE_URL


def test_database_health_check_with_loaded_database_url():
    """Verify health check connects to the actual database configured in Settings."""
    saved_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear()
    try:
        with TestClient(app) as live_client:
            response = live_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
    finally:
        app.dependency_overrides = saved_overrides


def test_health_endpoint_database_disconnected_logs_error(caplog):
    """Verify health check handles database failure gracefully and logs the error."""
    mock_db = MagicMock(spec=Session)
    mock_db.execute.side_effect = Exception("Simulated DB connection failure")

    def override_broken_db():
        yield mock_db

    saved_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_broken_db
    try:
        with caplog.at_level(logging.ERROR, logger="invoiceai"):
            with TestClient(app) as test_client:
                response = test_client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["database"] == "disconnected"
                assert any(
                    "Database health check failed: Simulated DB connection failure" in record.message
                    for record in caplog.records
                )
    finally:
        app.dependency_overrides = saved_overrides
