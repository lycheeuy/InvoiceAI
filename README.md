# InvoiceAI

AI-powered invoice processing with a web dashboard, structured data extraction, and a manual-review workflow.

InvoiceAI is a full-stack application designed to reduce repetitive invoice data entry. It uses a FastAPI backend and Google's Gemini API to extract invoice information from uploaded documents, stores invoice records in PostgreSQL, and presents processing results in a Next.js interface.

## Features

- **Invoice upload** — upload supported invoice documents in PDF, PNG, JPG, or JPEG format.
- **AI-assisted extraction** — extract key invoice information and line items with the Gemini API.
- **Invoice dashboard** — view invoice counts, processing statuses, recent invoices, and API/database health.
- **Invoice list and detail views** — inspect stored invoices and their extracted information.
- **Manual review workflow** — flag records that need attention, including cases where an amount could not be reliably extracted.
- **Persistent storage** — keep PostgreSQL data in a Docker volume and uploaded files in a host-mounted storage directory.
- **Containerized deployment** — run the frontend, backend, and database as separate Docker services.

> InvoiceAI is an evolving project. AI extraction should be checked against the original document before invoice data is used for accounting or payment decisions.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic |
| AI integration | Google Gemini API (`google-genai`) |
| Database | PostgreSQL 17 |
| ORM and migrations | SQLAlchemy 2, Alembic |
| Document handling | `pdfplumber`, Python multipart upload support |
| Deployment | Docker, Docker Compose |

## Architecture

```text
Browser
  │
  ▼
Next.js frontend :3000
  │  /api/v1 proxy
  ▼
FastAPI backend :8000 ──────► Google Gemini API
  │
  ▼
PostgreSQL :5432

Uploaded files ─────────────► Persistent storage volume
```

In the included production Compose configuration, the frontend is published on `127.0.0.1:3001` and the API on `127.0.0.1:8001`. PostgreSQL is reachable only within the Docker network and is not published to a host port.

## Current Application Flow

1. Upload an invoice document through the web interface.
2. The backend receives the file and starts document processing.
3. The Gemini integration extracts invoice information.
4. Invoice data and processing status are stored in PostgreSQL.
5. Review-needed or failed records can be inspected from the application.

Processing statuses used in the interface include `PROCESSED`, `NEEDS_REVIEW`, and `FAILED`.

## Requirements

- Linux server or development environment with Docker Engine and Docker Compose
- A Google Gemini API key with access to a supported model
- Git

## Run with Docker Compose

The following instructions use the included `docker-compose.prod.yml` file and are suitable for a Linux server. The Compose file expects a local `.env.production` file, which must not be committed to Git.

### 1. Clone the repository

```bash
git clone https://github.com/lycheeuy/InvoiceAI.git
cd InvoiceAI
```

### 2. Create the production environment file

```bash
cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production
```

Set the values for your environment. At minimum, replace the database password and Gemini API key placeholders. Use a strong, unique database password and a Gemini model identifier supported by your API project.

```dotenv
POSTGRES_USER=invoiceai_prod_user
POSTGRES_PASSWORD=replace_with_a_strong_unique_password
POSTGRES_DB=invoiceai_prod
FILE_STORAGE_PATH=/app/storage/invoices
MAX_UPLOAD_SIZE=5242880
ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg
CORS_ORIGINS=http://localhost:3001,http://127.0.0.1:3001
GEMINI_API_KEY=replace_with_your_gemini_api_key
GEMINI_MODEL=your_supported_gemini_model
```

`CORS_ORIGINS` is a comma-separated list of allowed browser origins. Adjust it for the way the frontend will be accessed. Do not place API keys, passwords, or actual production environment files in the repository.

### 3. Validate the configuration and build the images

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml build
```

### 4. Start the database

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d invoiceai-db
```

Wait for the database health check to report `healthy`:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

### 5. Apply database migrations

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm --workdir /app/backend invoiceai-api alembic upgrade head
```

### 6. Start the backend and frontend

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d invoiceai-api invoiceai-frontend
```

Check the service status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

## Verify the Deployment

With the production Compose configuration running on the same host, test the frontend and the API proxy:

```bash
curl -i http://127.0.0.1:3001/
curl -i http://127.0.0.1:3001/api/v1/health
```

The health endpoint should return HTTP `200` when the API is healthy and connected to the database.

To inspect backend logs:

```bash
docker logs --tail 100 invoiceai-api
```

## Access Through an SSH Tunnel

The Compose file binds the web and API ports to loopback addresses instead of exposing them directly to the public internet. To access the web interface from your own computer, create an SSH tunnel from your computer:

```bash
ssh -L 3101:127.0.0.1:3001 ubuntu@YOUR_SERVER_IP
```

Keep that terminal session open, then visit `http://127.0.0.1:3101` in your browser. Replace `ubuntu` and `YOUR_SERVER_IP` with the SSH username and address for your server.

**Security note:** the application does not yet provide a complete user authentication layer. Keep it private and do not expose it publicly until access control and production security requirements have been addressed.

## Configuration Reference

| Variable | Purpose |
|---|---|
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | PostgreSQL database name |
| `FILE_STORAGE_PATH` | Upload storage path inside the backend container |
| `MAX_UPLOAD_SIZE` | Maximum upload size in bytes; `5242880` is 5 MB |
| `ALLOWED_EXTENSIONS` | Permitted file extensions |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `GEMINI_API_KEY` | API key for Gemini integration |
| `GEMINI_MODEL` | Gemini model identifier used by the backend |

## Repository Structure

```text
InvoiceAI/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── app/                  # FastAPI application and services
│   └── requirements.txt
├── frontend/
│   ├── src/app/              # Next.js routes and pages
│   ├── src/lib/api.ts        # Frontend API client
│   ├── src/types/            # Shared frontend types
│   └── Dockerfile
├── docs/                     # Development notes and project documentation
├── Dockerfile                # Backend image
├── docker-compose.prod.yml   # Production-oriented Docker Compose setup
├── .env.production.example   # Environment variable template
└── README.md
```

## Data and Security Notes

- Never commit `.env.production`, `.env.local`, API keys, database passwords, or real invoice documents.
- Use synthetic or properly redacted invoices for development and testing.
- Confirm extracted values against the source document. Missing or uncertain line-item amounts should be reviewed rather than assumed to be zero.
- Back up the PostgreSQL volume and uploaded-file storage separately.
- Keep the database private; the Compose configuration does not publish PostgreSQL to a host port.

## Project Status

InvoiceAI is actively being developed. The current deployment includes the Next.js frontend, FastAPI backend, PostgreSQL database, Alembic migrations, and Gemini API integration. End-to-end invoice extraction and error handling should be validated in the target environment before relying on the system for real financial workflows.

## License

No license has been declared yet. Unless a license is added to this repository, the code should not be assumed to be open source or freely reusable.
