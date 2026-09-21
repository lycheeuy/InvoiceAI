# InvoiceAI — Development Roadmap & Implementation Plan

## 1. Project Monorepo Structure

```
InvoiceAi/
├── .github/
│   └── workflows/                # CI/CD pipelines (Linting, type-checking, automated tests)
├── docs/                         # Architectural blueprints & engineering specifications
│   ├── PROJECT_SPEC.md           # Business requirements, domain models & AI principles
│   ├── ARCHITECTURE.md           # System components, database schemas & REST API spec
│   └── DEVELOPMENT_ROADMAP.md    # Multi-phase execution blueprint (this file)
├── backend/                      # Python + FastAPI Application
│   ├── app/
│   │   ├── api/                  # HTTP Transport Layer
│   │   │   └── v1/
│   │   │       ├── endpoints/    # Route controllers (invoices.py, health.py)
│   │   │       └── router.py     # Aggregated v1 API router
│   │   ├── core/                 # Configuration, security & logging
│   │   │   ├── config.py         # Pydantic BaseSettings (.env loader)
│   │   │   └── logging.py        # Structured logging configuration
│   │   ├── db/                   # Database engine & session management
│   │   │   ├── base.py           # SQLAlchemy declarative base
│   │   │   └── session.py        # Async or sync sessionmaker
│   │   ├── models/               # SQLAlchemy ORM database models
│   │   │   ├── invoice.py        # Invoice and InvoiceLineItem tables
│   │   │   └── log.py            # ProcessingLog table
│   │   ├── schemas/              # Pydantic validation & transfer objects
│   │   │   ├── invoice.py        # Request/response DTOs for REST API
│   │   │   └── llm.py            # Gemini structured extraction schema
│   │   ├── services/             # Core business & processing logic
│   │   │   ├── document.py       # File inspection, MIME check & text extraction
│   │   │   ├── extractor.py      # Gemini API prompt client & structured parser
│   │   │   ├── validator.py      # Deterministic arithmetic & business validator
│   │   │   └── webhook.py        # Webhook dispatcher for n8n automation
│   │   └── main.py               # FastAPI entrypoint
│   ├── alembic/                  # Database migration scripts
│   ├── storage/                  # Local directory for uploaded files (gitignored)
│   │   └── invoices/
│   ├── tests/                    # Unit, integration, and mocked AI tests
│   │   ├── test_document.py      # PDF parsing tests
│   │   ├── test_validator.py     # Arithmetic & date logic tests
│   │   └── test_api.py           # FastAPI endpoint tests
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Backend container configuration
│   └── .env.example              # Sample environment variables
├── frontend/                     # Next.js + TypeScript Application
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── layout.tsx        # Global layout & navigation sidebar
│   │   │   ├── page.tsx          # Dashboard overview & summary statistics
│   │   │   ├── upload/page.tsx   # Drag-and-drop document upload interface
│   │   │   └── invoices/
│   │   │       ├── page.tsx      # Filterable invoice list table
│   │   │       └── [id]/page.tsx # Side-by-side split-screen review & inspector
│   │   ├── components/           # Reusable UI components
│   │   │   ├── DocumentViewer.tsx# PDF / Image viewer
│   │   │   ├── ExtractionForm.tsx# Structured fields & line items editor
│   │   │   ├── StatusBadge.tsx   # Color-coded lifecycle badge
│   │   │   └── UploadDropzone.tsx# File drag-and-drop zone
│   │   ├── lib/                  # Shared utilities & API client
│   │   │   ├── api.ts            # Fetch / Axios wrapper
│   │   │   └── types.ts          # TypeScript interfaces for API models
│   │   └── styles/               # Global CSS & Tailwind configuration
│   ├── package.json              # Node.js dependencies
│   ├── tsconfig.json             # TypeScript configuration
│   └── Dockerfile                # Frontend container configuration
├── automation/                   # n8n Automation Workflows & Config
│   ├── workflows/                # Exported JSON workflow definitions
│   │   ├── invoice_processed.json# Notification & spreadsheet sync workflow
│   │   └── invoice_escalation.json# Human-in-the-loop review alert workflow
│   └── README.md                 # Setup instructions for importing n8n flows
├── docker-compose.yml            # Local orchestration (Postgres, n8n, Backend, Frontend)
└── README.md                     # High-level project documentation & quickstart
```

---

## 2. Multi-Phase Implementation Plan

### Phase 0: Project Discovery & Architecture *(Current)*
- **Objective**: Establish complete clarity on requirements, domain models, AI principles, API design, database schemas, and engineering roadmap before writing any application code.
- **Key Features**: System architecture diagrams, field-level specifications, failure recovery matrix, interview preparation guide.
- **Deliverables**:
  - `docs/PROJECT_SPEC.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DEVELOPMENT_ROADMAP.md`
- **Exit Criteria**: All architectural questions answered, zero ambiguity on scope, approved roadmap.

---

### Phase 1: Environment, Database & Ingestion Foundation
- **Objective**: Establish the backend foundation, database connectivity, data models, file storage, and file upload validation.
- **Features**:
  - Project configuration with Pydantic `BaseSettings` reading from `.env`.
  - PostgreSQL database connection with SQLAlchemy ORM and Alembic migrations.
  - Initial database tables: `invoices`, `invoice_line_items`, and `processing_logs`.
  - Ingestion endpoint: `POST /api/v1/invoices/upload`.
  - Binary file inspection (magic bytes for PDF/PNG/JPEG, size cap at 10 MB).
  - SHA-256 binary hashing for instant duplicate rejection.
  - Safe file persistence using UUIDs under `backend/storage/invoices/`.
- **Testing Requirements**:
  - Unit tests for MIME type verification (valid PDF, valid PNG, disguised `.exe`).
  - Unit tests for file size rejection.
  - Integration test for upload endpoint verifying database row creation and duplicate hash conflict (`HTTP 409`).
- **Dependencies**: None.

---

### Phase 2: Document Processing Engine & OCR Pipeline
- **Objective**: Build the heuristic router that differentiates digital PDFs from scanned PDFs and images, extracting raw text cleanly.
- **Tasks**:
  - Task 1: Document Processing Core - COMPLETED
  - Task 2: Gemini Multimodal Adapter - COMPLETED
  - Task 3: Processing Service - COMPLETED
  - Task 4: BackgroundTasks + Upload Integration - COMPLETED
  - Task 5: Testing - COMPLETED
  - Task 6: Documentation + Final Verification - COMPLETED
- **Features**:
  - PDF inspection service using `pdfplumber` / `pypdf`.
  - Character density check ($\ge 100$ characters $\rightarrow$ digital text extraction; $< 100$ characters $\rightarrow$ scanned OCR route).
  - Text layout preservation to keep tabular structures legible for the LLM.
  - Image handling service for PNG, JPEG, and scanned PDF page renders.
  - Direct image routing preparation for Gemini Multimodal Vision.
  - Diagnostic event logging to `processing_logs` at each step.
- **Testing Requirements**:
  - Test digital PDF extraction with sample invoices (verify extracted text matches document content).
  - Test scanned PDF detection (verify heuristic correctly identifies image-only PDF).
  - Test raster image loading and validation.
- **Dependencies**: Phase 1 completion.
- **Status**: COMPLETED.

---

### Phase 3: AI Extraction, Structured Outputs & Validation Pipeline
- **Status**: NOT STARTED
- **Objective**: Implement Gemini API integration with structured JSON enforcement and the programmatic business logic validator.
- **Features**:
  - Integration of official `google-genai` SDK targeting `gemini-2.5-flash`.
  - Pydantic schema for structured output extraction (`ExtractedInvoiceData`).
  - Strict system prompt with anti-injection XML delimiters (`<invoice_document>`).
  - Fallback logic: text prompt for digital PDFs, multimodal image prompt for scans/photos.
  - Deterministic business validator service:
    - Math check: $\text{subtotal} + \text{tax} = \text{total} \pm 0.05$.
    - Line item sum check: $\sum \text{items} = \text{subtotal} \pm 0.05$.
    - Date sequence check: $\text{due\_date} \ge \text{invoice\_date}$.
    - ISO currency normalization.
  - Status classification logic (`PROCESSED` vs `NEEDS_REVIEW` vs `FAILED`).
  - Database persistence of validated headers, line items, and audit logs.
  - Asynchronous background execution via FastAPI `BackgroundTasks`.
  - Status polling endpoint: `GET /api/v1/invoices/{id}/status`.
- **Testing Requirements**:
  - Mocked LLM unit tests validating Pydantic parsing of perfect JSON.
  - Business validator tests with intentional math errors (verify transition to `NEEDS_REVIEW`).
  - Business validator tests with invalid dates (verify error flags).
  - End-to-end integration test: Upload invoice $\rightarrow$ process in background $\rightarrow$ verify DB state.
- **Dependencies**: Phase 2 completion.

---

### Phase 4: n8n Workflow Automation & Webhooks
- **Objective**: Implement event-driven webhook dispatching and configure end-to-end automation workflows in n8n.
- **Features**:
  - FastAPI webhook dispatcher service with HMAC-SHA256 signature generation.
  - Webhook triggers for `invoice.processed`, `invoice.needs_review`, and `invoice.failed`.
  - Local n8n instance setup (via Docker Compose or local npm).
  - Success Workflow in n8n:
    - Webhook receiver verifying signature.
    - Format Discord / Slack notification card with vendor name, total, and invoice number.
    - Append record row to Google Sheets or mock financial ledger.
  - Escalation Workflow in n8n:
    - Receive `invoice.needs_review` event.
    - Post alert to Slack/Email with direct link to the Next.js review page.
- **Testing Requirements**:
  - Unit test for webhook HMAC signature generator.
  - Webhook dispatch test verifying payload delivery to an HTTP mock / test receiver.
  - End-to-end trigger verification from FastAPI through n8n.
- **Dependencies**: Phase 3 completion.

---

### Phase 5: Next.js Frontend Dashboard & Document Inspector
- **Objective**: Build a responsive Next.js/TypeScript frontend for uploading, tracking, and reviewing invoices.
- **Features**:
  - Upload view: Drag-and-drop dropzone with file size/type validation and upload progress.
  - Dashboard view: Summary KPI metric cards (Total Processed, Pending Review, Failures) and recent invoices table.
  - Filterable invoice table: Filter by status badge (`PROCESSED`, `NEEDS_REVIEW`, `FAILED`), search by vendor.
  - Split-screen invoice inspector (`/invoices/[id]`):
    - Left side: Original PDF / Image viewer with zoom and scroll.
    - Right side: Interactive editable form showing extracted header data and line items.
    - Warning highlights on fields that failed validation.
    - "Approve & Sync" button that submits `PATCH /api/v1/invoices/{id}/review`.
- **Testing Requirements**:
  - Component rendering tests.
  - E2E happy path: Upload file from UI $\rightarrow$ observe status change $\rightarrow$ inspect extracted data in split view.
  - Review flow test: Edit field $\rightarrow$ click approve $\rightarrow$ verify updated status in DB.
- **Dependencies**: Phase 1, Phase 3, Phase 4 completion.

---

### Phase 6: Polish, Dockerization, Testing & Portfolio Demonstration
- **Objective**: Containerize the complete application with Docker Compose, prepare test datasets, write clear documentation, and produce demo artifacts.
- **Features**:
  - Multi-container `docker-compose.yml` orchestrating PostgreSQL, FastAPI backend, Next.js frontend, and n8n.
  - Curated test dataset of invoices:
    - 3 digital-native PDFs (clean, single-page, multi-item).
    - 2 scanned PDFs (raster images).
    - 2 mobile receipt photos.
    - 1 invoice with intentional arithmetic error (to demonstrate `NEEDS_REVIEW` escalation).
  - Comprehensive root `README.md` with architectural diagrams, technology justifications, local setup guide, and portfolio showcase highlights.
  - Video demo / walkthrough script illustrating the entire AI engineering lifecycle.
- **Testing Requirements**:
  - Full clean-slate `docker compose up --build` verification.
  - Zero-to-hero smoke test: Upload all test documents and verify expected statuses.
- **Dependencies**: All prior phases.

---

## 3. Solo Developer Risk Mitigation & Guardrails

| Pitfall / Risk | How It Can Derail the Project | Architectural Guardrail |
| :--- | :--- | :--- |
| **Over-engineering Auth / Multi-tenancy early** | Spending days configuring NextAuth, JWT, refresh tokens, and RBAC before having a working AI extraction pipeline. | **Rule**: Build zero user authentication for the MVP. Run as an internal AP tool on `localhost`. Add auth only after core AI workflows work. |
| **Complex OCR binary compilation in Docker** | Getting stuck debugging C++ dependencies (Tesseract, Leptonica, Poppler) inside Docker containers. | **Rule**: Use `pdfplumber` for digital text; use Gemini's native multimodal vision for scanned documents. This keeps backend dependencies 100% pure Python. |
| **Redis / Celery Infrastructure Sprawl** | Managing Redis containers, message brokers, worker processes, and connection states before validating the pipeline. | **Rule**: Use FastAPI `BackgroundTasks` for the MVP. It runs in-process asynchronously and requires zero additional infrastructure. |
| **Fragile Regex Post-Processing** | Writing hundreds of lines of brittle regular expressions to parse dates, currencies, and invoice numbers from raw text. | **Rule**: Let Gemini handle semantic parsing into structured JSON, then use Pydantic models for strict type validation. Use regex only for simple string sanitization. |
| **Unbounded LLM Cost & Rate Limits** | Running expensive multimodal prompts on every single document or entering infinite retry loops. | **Rule**: Always prioritize digital text extraction ($< 500$ input tokens). Cap retries to 2 attempts with exponential backoff. Cache file hash to prevent re-processing identical uploads. |

---

## 4. Milestone Verification Checklist

- [ ] **Milestone 1**: A valid PDF can be uploaded via `curl`, its hash is verified, and a row is inserted into PostgreSQL.
- [ ] **Milestone 2**: Text is extracted from digital PDFs in under 50ms with zero OCR overhead.
- [ ] **Milestone 3**: Extracted document content is processed by Gemini, returning valid structured JSON matching our Pydantic schema 100% of the time.
- [ ] **Milestone 4**: Invoices with deliberate math discrepancies are automatically flagged as `NEEDS_REVIEW` with exact error messages.
- [ ] **Milestone 5**: n8n webhook fires reliably upon invoice processing, sending an alert to a notification channel.
- [ ] **Milestone 6**: Next.js dashboard displays all invoices, allows upload, and offers a split-screen inspection view.
- [ ] **Milestone 7**: Complete application spins up with a single `docker compose up` command.
