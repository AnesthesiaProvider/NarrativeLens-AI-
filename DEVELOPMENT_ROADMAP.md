# Development Roadmap

## Completed or substantially present

- FastAPI API with health, investigation, analysis, ingestion/scanner, narrative, coordination, feedback and evaluation route modules.
- React 19 dashboard with overview, investigations, text/meme analysis, scanner, narratives, evidence, coordination, evaluation, feedback, datasets and settings pages.
- SQLAlchemy relational model for investigations, source/document/media/OCR/classification, narrative cluster, coordination, review/feedback, dataset/model evaluation and audit records.
- XLM-R classifier training/evaluation assets and a saved fine-tuned checkpoint; model manager supports lazy loading.
- Multiple platform scraper implementations, URL/file validation helpers and heuristic target/harm/severity enrichment.
- Backend pytest suite and manual inference/live API scripts.

“Present” means source/assets exist; production readiness and live integrations are not implied.

## Prioritized pending work

### P0 — Security and safe operation

- Add authentication, role-based authorization and per-route access controls, especially for model management, evaluation, feedback and data deletion.
- Replace default development secret/configuration with fail-fast production validation; restrict CORS, methods and API docs outside development.
- Add request rate/size/time limits. Treat URL scanning as SSRF-sensitive: revalidate redirects and the actual connected IP; constrain schemes, ports, response sizes and timeouts.
- Enforce actual file MIME/content validation, safe storage names, and upload scanning; make the configured upload limit apply consistently to streamed content.
- Avoid returning exception class and potentially sensitive error details to clients; redact logs and define retention controls for collected content.

### P1 — Make setup reproducible

- Add and verify backend/frontend Dockerfiles; align Compose environment names (`VITE_API_BASE_URL` versus `VITE_API_URL`) and health checks.
- Choose explicit production DB behavior; do not silently move failed PostgreSQL workloads to a local SQLite file.
- Add Alembic revisions and test empty-database upgrade and existing-database migration paths.
- Document true dependencies, CPU/GPU model requirements, model acquisition and external credentials without claiming integrations that are not wired.

### P1 — Verify core workflows

- Run backend tests plus end-to-end checks for investigation creation → ingestion → classification/OCR → persistence → review/feedback.
- Test scraper adapters against fixtures and controlled live endpoints; record failure modes, legal/platform constraints and retry behavior.
- Verify model artifact loading, device behavior, latency/memory and error fallback on supported Python/PyTorch environments.
- Validate model quality with held-out, subgroup and multilingual datasets; publish confidence/threshold caveats and human review guidance.

### P2 — Data and architecture

- Add a frontend API contract layer with typed response schemas and remove broad `any` types/fallback calls where routes are stable.
- Decide whether semantic clustering/vector search, Redis caching/queueing, grounded RAG generation and Captum explainability are in scope; implement and measure or remove unsupported claims.
- Add DB indexes based on query plans, pagination on collection endpoints, and transaction boundaries for multi-step ingestion.
- Separate ingestion jobs from request workers if scrape/model workloads block API responsiveness; set concurrency and model singleton behavior for multi-worker deployment.

### P2 — Quality and observability

- Add frontend unit/component tests and API contract tests; expand backend coverage for auth, SSRF, upload boundaries, migrations and failure paths.
- Add structured redacted logs, metrics, tracing, readiness checks and alertable model/database dependency status.
- Add lint/typecheck/security/dependency checks to CI; current repo evidence does not include a verified CI workflow.

## Known bugs and risks to resolve

- No auth/authorization implementation found.
- Default settings include development secret and permissive development behavior.
- URL checks may not bind DNS validation to outbound connection; redirects need equivalent checks.
- Upload MIME rejection is a no-op; file extension is not content verification.
- DB initialization catches failure and switches silently to SQLite, risking split/ephemeral data.
- Alembic revisions absent; startup relies on metadata table creation.
- README and compose describe capabilities/dependencies that differ from implementation (pgvector/HNSW, Redis integration, Qwen generation, Captum, OCR/GPU, deployment Dockerfiles).
- No frontend test command/framework in package scripts.
- Potential CPU-bound model inference and scraping inside async request paths; concurrency/load testing not evidenced.

## Existing TODO/FIXME scan

No explicit TODO/FIXME markers were found in reviewed source directories. Several deliberate `pass` blocks and broad exception fallbacks remain; these require local context review and are not automatically unfinished tasks.

## Recent Git history

The working tree was clean. Latest commit at inspection: `3633d09` (2026-10-28, documentation citation update). Recent commits include research-report revisions, scanner fixes, local LLM configuration and narrative analysis changes. Git does not capture uncommitted local data/model assets or confirm deployed behavior.
