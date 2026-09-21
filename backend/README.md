# InvoiceAI Backend

FastAPI backend service for ingestion, validation, and storage of invoice documents.

## Prerequisites
- **Python**: 3.11+ (Tested on Python 3.12)
- **PostgreSQL**: 15+ running locally or in a container (port 5432)

---

## Quickstart Setup

### 1. Create and Activate Virtual Environment
```powershell
# From the project root (InvoiceAi/)
python -m venv backend\.venv

# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1

# Linux / macOS:
source backend/.venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item backend\.env.example backend\.env
```
Edit `backend/.env` with your PostgreSQL database credentials:
```env
DATABASE_URL="postgresql+psycopg://<username>:<password>@localhost:5432/invoiceai"
FILE_STORAGE_PATH="storage/invoices"
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS="pdf,png,jpg,jpeg"
```

---

## Database Setup & Alembic Migrations

Ensure your PostgreSQL instance is running and create the `invoiceai` database:
```sql
CREATE DATABASE invoiceai;
```

Run Alembic migrations to create all required tables (`invoices`, `invoice_line_items`, `processing_logs`):
```powershell
cd backend
alembic upgrade head
```

---

## Running the Application

Start the development server with hot-reload enabled:
```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

- **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **Health Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Running Automated Tests

The test suite runs against an isolated in-memory SQLite database and isolated temporary file storage:
```powershell
pytest backend/tests -v
```
All 12 automated unit and integration tests will execute without requiring live database credentials.
