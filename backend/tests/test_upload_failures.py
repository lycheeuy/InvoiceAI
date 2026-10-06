import io
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.invoice import Invoice
from backend.app.models.log import ProcessingLog

def test_upload_database_commit_failure_rolls_back(client: TestClient, db_session: Session, valid_pdf_bytes: bytes):
    """Test that a database commit failure during upload results in a 500 error and no partial records."""
    
    original_commit = db_session.commit
    
    def failing_commit():
        raise Exception("Simulated database commit failure")
        
    with patch.object(db_session, "commit", side_effect=failing_commit):
        files = {"file": ("invoice_fail.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/invoices/upload", files=files)
        
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DATABASE_ERROR"
    
    # Ensure no invoice was actually saved to the database (since rollback should have occurred)
    # The session might be invalid after a failed commit in SQLAlchemy, so we rollback just in case
    # then check if any record with that file name exists.
    db_session.rollback()
    
    invoices = db_session.query(Invoice).filter(Invoice.file_name == "invoice_fail.pdf").all()
    assert len(invoices) == 0
