# Technical Documentation

> The original user request ended after “TECHNICAL_DOCUMENTATION.md — Fo”. This file records the technical documentation supported by repository inspection; additional intended sections were not available.

## Repository map

- `backend/app/main.py`: FastAPI lifespan, CORS, exception handlers, root and router mounting.
- `backend/app/api/`: HTTP endpoints for health, investigation lifecycle, text/image analysis, scanning/ingestion, narrative reports, coordination, feedback and evaluations.
- `backend/app/core/`: Pydantic Settings, async SQLAlchemy engine/session and URL/text/HTML/file security utilities.
- `backend/app/db/models.py`: relational entities and ORM associations.
- `backend/app/schemas/`: request/response schemas.
- `backend/app/services/`: OCR, narrative/comment services and platform scraper adapters.
- `backend/app/ml/`: lazy model manager and enrichment pipeline.
- `backend/tests/`: pytest API/service tests; `scripts/`: manual inference and live API probes.
- `frontend/src/`: routed React SPA, pages, shared components, hooks, types and API wrapper.
- `ml/`: training, datasets, preference-pair generation and evaluation scripts/results/checkpoints.
- `docs/`: architecture/methodology/governance/research outline.
- Generated/large assets present locally include virtual environments, `node_modules`, `dist`, model caches/checkpoints, uploaded files and SQLite DBs. They are excluded from source-level architecture assumptions and should not be treated as dependency manifests.

## Runtime commands

Commands implied by project files/documentation (not executed during this audit):

```powershell
# Backend, from repository root after installing backend/requirements.txt
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend, in another terminal
cd frontend
npm install
npm run dev

# Build and lint frontend
npm run build
npm run lint

# Backend tests, from repository root
pytest backend/tests

# Manual inference scripts, from repository root
python scripts/test_inference.py
python scripts/test_live_api.py

# Compose, if the referenced Dockerfiles are supplied
docker compose up --build
```

The backend `pyproject.toml` explicitly excludes Python 3.13, while the local virtual environment appears to be Python 3.13; use Python 3.11 or 3.12 for a supported clean install. `npm run build` invokes TypeScript project compilation plus Vite. There is no frontend test script. Backend tests are configured for pytest/pytest-asyncio. ML training/evaluation scripts are separate research workflows and can require large downloads/compute.

## Dependencies and configuration

Backend requirements include FastAPI/Uvicorn, SQLAlchemy, asyncpg/psycopg2, Alembic, Pydantic Settings, multipart/aiofiles/httpx, Redis client, PyTorch/Transformers/sentence-transformers, scikit-learn, NetworkX, SHAP, NumPy/Pandas, Pillow/imagehash, feedparser, BeautifulSoup/lxml, aiosqlite, Captum, datasets and PyYAML. `pyproject.toml` also lists optional developer packages (pytest-cov, Black, Ruff, mypy).

Frontend production dependencies include React/DOM, React Router, TanStack Query, react-hook-form/resolvers, Zod, Recharts, Lucide, clsx and tailwind-merge; dev dependencies include Vite, TypeScript, Tailwind, React plugin and Oxlint. `@tanstack/react-query-devtools` is imported by source but is not declared in the shown package manifest, a likely clean-install/build issue. `@types/react-router-dom` is a v5 type package alongside React Router v7 and may be unnecessary/incompatible. Dependency usage has not been exhaustively reconciled.

Environment variable *names* are listed in `.env.example` and `backend/.env.example`; values are intentionally omitted. Backend settings directly consume project/env/debug/secret/CORS, PostgreSQL or explicit async DB URL, Redis, device/model IDs/cache/checkpoint path, batch/sequence settings, upload location/limit, blocked networks, allowed source types, YouTube/Reddit credentials and Ollama configuration. The root template also advertises several values not consumed in backend `Settings` (such as some generation/search/provider/rate-limit names). Backend `.env` exists locally; its contents were not read or reproduced. Do not commit it.

Database: PostgreSQL 16/pgvector image is in Compose; app ORM uses SQLAlchemy and PostgreSQL URLs, with automatic SQLite fallback. Redis 7 is provisioned in Compose, though runtime use was not confirmed. Two SQLite DB files exist locally. Model weights are cached under `model_cache`/`backend/model_cache` and trained XLM-R artifacts under `ml/checkpoints`; a clean machine may need model downloads.

## API inventory

All routes are mounted below `/api`. Router modules expose health/status/model routes, investigation CRUD and related documents/narratives, text/image/comment analysis, universal scanner, ingestion endpoints, narrative/report/scrape endpoints, coordination analysis, feedback, and model evaluation/dataset operations. Source of truth is endpoint decorators in `backend/app/api/*.py`; OpenAPI is generated at `/openapi.json`, with docs at `/docs` by default. Authentication is absent, so the existence of a route does not imply access control.

Frontend origin uses `VITE_API_URL` or `/api`. The Docker Compose file supplies `VITE_API_BASE_URL`, a mismatch. Multipart uploads are handled by browser `FormData`; JSON calls use the shared wrapper and normalize error responses into `ApiError`.

## Models and training

The tracked model pipeline includes classifier training with XLM-R, focal-loss helper, DPO preference data generation/training code, evaluation and threshold optimization, benchmark report JSON, and saved checkpoints. Backend model manager chooses CUDA when available, otherwise CPU, and loads configured classifier/embedding/multimodal resources lazily. The enrichment pipeline detects targets/harm using rule-based classes and computes severity. Treat claims of model quality, calibration, multilingual coverage and GPU acceleration as unverified until reproducible evaluation on clean supported environments.

## Security and limitations

- No login, session/JWT validation, user identity or authorization dependency found.
- Development defaults exist for secret, debug and local services; production configuration should fail closed.
- CORS permits credentials and configured origins; default list includes localhost variants.
- SSRF helper checks schemes and DNS answers for private/reserved IPs, but downstream redirect and DNS rebinding controls need verification.
- File validation checks size/extension, but MIME mismatch branch is a no-op and there is no observed magic-byte verification.
- Model and scraper work in request handlers may consume substantial CPU/network time; no task queue integration was verified.
- Error logging may include exception text and validation detail; review for sensitive payload leakage.
- Startup schema creation is convenient for development but there are no actual Alembic migration revisions in the repo.
- README lists capabilities such as pgvector/HNSW, Redis inference cache/broker, grounded RAG, Qwen generation, and Captum integrated gradients; implementation evidence is incomplete or mismatched. Verify before relying on or advertising them.

## Test coverage

Backend tests cover health, investigations, ingestion/narratives, narrative scraping, hate comments and analysis. The repository also has manual inference/API scripts. No frontend unit or integration tests are defined in `package.json`. Tests were not run as part of this documentation-only audit.
