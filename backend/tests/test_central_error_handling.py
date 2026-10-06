import logging
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.core.exceptions import AppException
from backend.app.core.handlers import register_exception_handlers

@pytest.fixture
def test_app():
    app = FastAPI()
    register_exception_handlers(app)
    
    @app.get("/api/v1/test_error/app-exception")
    def trigger_app_exception():
        raise AppException(
            message="This is a test application exception.",
            status_code=400,
            code="TEST_ERROR",
            details={"foo": "bar"}
        )
    
    @app.get("/api/v1/test_error/unexpected")
    def trigger_unexpected():
        raise ValueError("Secret traceback info here")
        
    return app


def test_app_exception_handling(test_app):
    """Test that AppException is correctly formatted into an ErrorResponse."""
    with TestClient(test_app) as client:
        response = client.get("/api/v1/test_error/app-exception")
        
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "TEST_ERROR"
    assert data["error"]["message"] == "This is a test application exception."
    assert data["error"]["details"] == {"foo": "bar"}
    
def test_unexpected_exception_handling(test_app, caplog):
    """Test that unexpected exceptions are caught and sanitized."""
    with caplog.at_level(logging.ERROR):
        with TestClient(test_app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/test_error/unexpected")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    # Notice the code from handlers.py is INTERNAL_SERVER_ERROR
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected error occurred."
    
    # Traceback should not be in the response
    assert "Secret traceback" not in response.text
    # But it should be in the logs
    assert any("Secret traceback info here" in record.message for record in caplog.records)
