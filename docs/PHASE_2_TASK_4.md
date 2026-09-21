# Phase 2 Task 4: BackgroundTasks + Upload Integration

## Objective
Connect the file ingestion pipeline to the document processing engine asynchronously, ensuring that API requests for uploads return quickly while AI extraction continues in the background.

## Previous Problem
Previously, the `upload_invoice` endpoint would validate and persist an uploaded file to disk and record an initial `PENDING` status in the PostgreSQL database. However, the system completely lacked any trigger mechanism to route the stored file into the `DocumentRouter`. The invoice effectively stalled at `PENDING` with no automated progression to `EXTRACTING` or `PROCESSED`.

## BackgroundTasks Integration
FastAPI's built-in `BackgroundTasks` feature was added to bridge the upload and processing layers. 

### Why a Fresh DB Session is Required
The `upload_invoice` endpoint operates within the lifecycle of an HTTP request, utilizing a request-scoped `db_session`. When the HTTP response is returned to the client, FastAPI (via its dependency injection generator) automatically calls `db.close()`. 
If we were to pass that same `db` reference to the background task, the task would attempt to query or commit using a closed SQLAlchemy session, resulting in `DetachedInstanceError` or connection exceptions. 
To solve this safely:
1. `process_invoice_background(invoice_id)` is the registered background task wrapper.
2. It accepts an `invoice_id` (a simple UUID), not the ORM object or session.
3. It provisions a completely fresh SQLAlchemy `SessionLocal()`, executes the pipeline, and reliably closes the session in a `finally` block.

## Upload and Status Lifecycle
1. **Validation**: Endpoint validates file extension, magic bytes, size limits, and checks for SHA-256 duplication.
2. **Persistence**: The file is stored locally, and an invoice record is created in PostgreSQL with status `PENDING`.
3. **Commit**: The database transaction is fully committed to ensure the record exists before any background task attempts to read it.
4. **Enqueue**: `BackgroundTasks.add_task()` queues `process_invoice_background`.
5. **Response**: A `202 Accepted` response returns to the client immediately.
6. **Execution**: After the HTTP response completes, FastAPI runs the background task, shifting the status from `PENDING` -> `EXTRACTING` -> (`PROCESSED` | `FAILED`).

## Response Behavior
The endpoint still returns a `202 Accepted` status, but the success message has been updated:
```json
{
  "message": "Invoice uploaded successfully. Processing has been queued.",
  "status": "PENDING"
}
```
This correctly sets user expectations that data extraction is happening asynchronously.

## Testing Approach
* A test verifies that `BackgroundTasks.add_task` is called accurately with the wrapper function.
* A specific test validates the isolation of the `process_invoice_background` wrapper, confirming it spins up a new DB session.
* The `BackgroundTasks` runner is mocked during endpoint testing so that real external APIs (Gemini) are never incidentally triggered in an upload unit test.

## Limitations of FastAPI BackgroundTasks
`BackgroundTasks` runs in the same event loop as the FastAPI server memory space. It is an excellent mechanism for MVP async jobs. However, it is **not a durable job queue**. 
* If the FastAPI server crashes or is restarted during processing, the background tasks are lost.
* There is no built-in retry mechanism or dead-letter queue.
If processing durability or horizontal scaling of worker nodes becomes necessary, the architecture must transition to a message broker solution (like Celery/RabbitMQ or Google Cloud Pub/Sub) in the future.
