# Phase 6 Task 3: VPS & Deployment Preparation

## Target VPS Architecture

The InvoiceAI production environment is designed to operate on a single VPS running Ubuntu 24.04 with Docker and Docker Compose. It operates alongside the existing ThoraxVision deployment, isolated via distinct container ports and host bindings.

```mermaid
flowchart TD
    Internet([Internet (HTTPS)]) --> Caddy

    subgraph Host[VPS Host (Ubuntu 24.04)]
        Caddy[Caddy Reverse Proxy]

        subgraph TV[ThoraxVision]
            TVAPI[ThoraxVision API]
        end

        subgraph InvoiceAI[InvoiceAI Docker Compose]
            API[invoiceai-api]
            DB[(invoiceai-db)]
            Network((invoiceai-network))

            API <--> Network
            DB <--> Network
        end

        Caddy -- "127.0.0.1:8000" --> TVAPI
        Caddy -- "127.0.0.1:8001" --> API
    end
```

### Port Allocation
- **ThoraxVision Backend:** Bound to `127.0.0.1:8000`. (Untouched and explicitly undisturbed).
- **InvoiceAI Backend:** Bound to `127.0.0.1:8001`.
- **InvoiceAI PostgreSQL:** Internal container port `5432` only on the isolated `invoiceai-network`. **No host port is published**, meaning the database is inaccessible from the internet or the host, keeping data secure.

## Persistence Strategy

### 1. Invoice File Storage
File storage must survive container recreation and upgrades. The architecture uses a bind mount for predictable, easy-to-manage storage on the host filesystem:
- **Host Path:** `/opt/invoiceai/storage`
- **Container Path:** `/app/storage`

This keeps invoice files completely separate from the container's ephemeral filesystem.

### 2. PostgreSQL Persistence
Database data is managed via a Docker named volume to ensure it persists across `docker compose down` and container upgrades.
- **Volume Name:** `invoiceai-db-data`
- **Container Path:** `/var/lib/postgresql/data`

*Note for production maintenance: Never use `docker compose down -v` unless you intend to completely destroy the database data permanently.*

## Required Environment Variables

A template file `.env.production.example` has been created. The required variables are:

```env
POSTGRES_USER=invoiceai_prod_user
POSTGRES_PASSWORD=<strong-db-password>
POSTGRES_DB=invoiceai_prod
DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@invoiceai-db:5432/${POSTGRES_DB}

FILE_STORAGE_PATH=/app/storage/invoices
MAX_UPLOAD_SIZE=5242880
ALLOWED_EXTENSIONS=["pdf", "png", "jpeg", "jpg"]
CORS_ORIGINS=["https://alifreezi.site", "https://api.alifreezi.site"]

GEMINI_API_KEY=<your-api-key>
GEMINI_MODEL=gemini-2.5-flash
```

## DNS Requirements
- The domain `alifreezi.site` (frontend) must be configured to point to its respective hosting (Vercel, Netlify, etc.).
- The domain `api.alifreezi.site` must have an A record pointing to the VPS IP address.

## Caddy Configuration (To Be Applied Later)
When deploying to the VPS, the existing system Caddyfile will need to be updated. The planned addition is:

```caddyfile
api.thoraxvision.site {
    reverse_proxy 127.0.0.1:8000
}

api.alifreezi.site {
    reverse_proxy 127.0.0.1:8001
}
```

## Planned Deployment Commands
When performing the initial deployment, the following commands will be executed on the VPS:

```bash
# 1. Create the persistent storage directory
sudo mkdir -p /opt/invoiceai/storage/invoices
sudo chown -R 1000:1000 /opt/invoiceai/storage  # Ensure container user permissions if dropping root

# 2. Clone the repository and checkout production branch
# 3. Setup environment configuration
cp .env.production.example .env.production
nano .env.production

# 4. Start the stack
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 5. Apply database migrations
docker compose -f docker-compose.prod.yml exec invoiceai-api alembic upgrade head
```

## Rollback Considerations
If the deployment fails or causes unintended issues, the application can be cleanly stopped using:
```bash
docker compose -f docker-compose.prod.yml down
```
This leaves the database volume and the storage directory entirely intact.
To ensure the existing ThoraxVision backend is perfectly preserved, its configuration and ports (8000) are explicitly ignored by InvoiceAI. **ThoraxVision must remain completely untouched during the entire deployment process.**
