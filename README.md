# NarrativeLens AI 🔍🛡️

> **Multilingual, Multimodal Hate Speech & Toxic Narrative Detection with Grounded Counter-Narrative Generation**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?logo=postgresql)](https://github.com/pgvector/pgvector)

---

## 📌 Overview

**NarrativeLens AI** is an end-to-end artificial intelligence platform engineered to detect, cluster, analyze, and counter hate speech and hostile disinformation campaigns across multiple languages and modalities. 

Rather than treating toxic language as isolated keywords or purely binary classifications, NarrativeLens captures **semantic narrative motifs** (such as conspiracy tropes, dehumanization metaphors, and coordinated harassment patterns). It pairs state-of-the-art vision-language reasoning for multimodal memes with retrieval-augmented **grounded counter-narrative generation** to support human moderators with constructive, empathetic de-escalation tools.

---

## ✨ Key Features

- 🌐 **Multilingual Cross-Lingual Detection**: Fine-tuned on `FacebookAI/xlm-roberta-base` for zero-shot and few-shot classification across 100+ languages, including code-mixed vernaculars.
- 🖼️ **Multimodal Meme & Visual Analysis**: Direct visual-textual reasoning via `Qwen/Qwen3-VL-4B-Instruct` to detect benign-conflict memes, visual dog-whistles, and hateful iconography.
- 🧬 **Dense Narrative Clustering**: High-dimensional semantic embeddings via `BAAI/bge-m3` combined with PostgreSQL `pgvector` HNSW indexing to uncover emergent narrative clusters and coordinated disinformation campaigns.
- 💡 **Grounded Counter-Narrative Generation**: Retrieval-augmented generation (RAG) powered by `Qwen/Qwen3-4B`, synthesizing evidence-backed, empathetic, and de-escalating responses to defuse toxic rhetoric.
- 🎯 **Explainability & Attribution**: Token-level saliency and rationales highlighting specific linguistic spans responsible for toxicity classifications.
- 🛡️ **Responsible AI & Governance**: Built-in PII scrubbing, annotator welfare safeguards, subgroup bias audits (BPSN/BNSP), and content-blurring moderator controls.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Ingestion & Preprocessing"]
        Input["Raw Input\n(Text, Image, Meme)"] --> Clean["Sanitizer & PII Scrubber"]
    end

    subgraph ML ["2. Machine Learning Inference Engine"]
        Clean --> XLM["XLM-RoBERTa-base\n(Multilingual Classifier)"]
        Clean --> VL["Qwen3-VL-4B\n(Multimodal Reasoner)"]
        Clean --> BGE["BAAI/bge-m3\n(Dense 1024d Embeddings)"]
    end

    subgraph Persistence ["3. Persistence & Search Layer"]
        BGE --> PG[("PostgreSQL 16 + pgvector\n(HNSW Vector Index & Relational DB)")]
        BGE --> Redis[("Redis 7\n(Inference Cache & Broker)")]
    end

    subgraph Mitigation ["4. Counter-Narrative Generation"]
        PG --> RAG["RAG Evidence Retrieval"]
        RAG --> QWEN["Qwen3-4B\n(Grounded Counter-Narrative)"]
    end

    subgraph Presentation ["5. Moderation Workbench"]
        XLM --> API["FastAPI Application Gateway"]
        VL --> API
        QWEN --> API
        API --> UI["React 18 + Tailwind SPA Dashboard"]
    end
```

---

## 💻 Tech Stack

| Layer | Technologies |
|---|---|
| **Backend API** | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Uvicorn |
| **Machine Learning** | PyTorch, Hugging Face Transformers, Accelerate, PEFT/LoRA, BitsAndBytes |
| **NLP & Vision Models** | `FacebookAI/xlm-roberta-base`, `BAAI/bge-m3`, `Qwen/Qwen3-VL-4B`, `Qwen/Qwen3-4B` |
| **Databases & Cache** | PostgreSQL 16 with `pgvector` (HNSW indexing), Redis 7 |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Lucide Icons, Recharts |
| **Infrastructure** | Docker, Docker Compose, PowerShell / Bash |

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/) installed
- *Or* for local manual execution: Python 3.11+, Node.js 18+, PostgreSQL 16 with pgvector, and Redis 7.

### Option A: Running with Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/narrativelens-ai.git
   cd narrativelens-ai
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Start services:**
   ```bash
   docker compose up --build
   ```

4. **Access the application:**
   - **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   - **Backend API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **PostgreSQL**: `localhost:5432` (database: `narrativelens`)
   - **Redis**: `localhost:6379`

---

### Option B: Manual Local Setup

#### 1. Database & Cache Services
Ensure PostgreSQL with `pgvector` and Redis are running locally. You can quickly launch just the dependencies using Docker:
```bash
docker compose up -d db redis
```

#### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure your database credentials in `.env` match your local instances.

#### 3. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate a Python virtual environment
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations (when initialized)
# alembic upgrade head

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. Frontend Setup
```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Install Node.js packages
npm install

# Start Vite development server
npm run dev
```

---

## ⚙️ Environment Variables

A template is provided in [`.env.example`](.env.example). Primary configurable parameters include:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL connection string with asyncpg | `postgresql+asyncpg://narrativelens:narrativelens@localhost:5432/narrativelens` |
| `DATABASE_SYNC_URL` | Sync PostgreSQL connection string | `postgresql://narrativelens:narrativelens@localhost:5432/narrativelens` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CLASSIFIER_MODEL_ID` | Model identifier for multilingual text classifier | `FacebookAI/xlm-roberta-base` |
| `EMBEDDING_MODEL_ID` | Model identifier for dense narrative vector embeddings | `BAAI/bge-m3` |
| `VISION_MODEL_ID` | Vision-language model for multimodal meme analysis | `Qwen/Qwen3-VL-4B-Instruct` |
| `GENERATION_MODEL_ID` | LLM for grounded counter-narrative generation | `Qwen/Qwen3-4B` |
| `MODEL_DEVICE` | Hardware device allocation (`auto`, `cuda`, `cpu`) | `auto` |
| `MODEL_LOAD_MODE` | Memory loading strategy (`lazy`, `eager`) | `lazy` |
| `SECRET_KEY` | Application secret key for JWT session encryption | `change-me-in-production` |

---

## 📁 Project Structure

```
.
├── .env.example                 # Example configuration environment variables
├── .gitignore                   # Multi-language & ML gitignore rules
├── docker-compose.yml           # Multi-service composition (db, redis, backend, frontend)
├── README.md                    # Project documentation
├── backend/                     # FastAPI application source code
├── frontend/                    # React / Vite / Tailwind UI source code
├── ml/                          # Machine learning module
│   ├── README.md                # ML architecture & training strategy
│   ├── datasets/                # Dataset acquisition & processing scripts (.gitkeep)
│   ├── training/                # Fine-tuning pipelines & loss functions (.gitkeep)
│   ├── evaluation/              # Benchmark & bias evaluation scripts (.gitkeep)
│   └── experiments/             # Experiment configs & run logs (.gitkeep)
├── docs/                        # Deep-dive documentation
│   ├── architecture.md          # Complete architectural specification
│   ├── methodology.md           # Research methodology, taxonomy & limitations
│   ├── data-governance.md       # Privacy, PII scrubbing & annotator welfare policy
│   ├── research-paper-outline.md # 13-section ACL research paper blueprint
│   └── model-cards/             # Standardized model cards (.gitkeep)
└── scripts/                     # Operational & deployment scripts (.gitkeep)
```

---

## 📖 In-Depth Documentation

- 📐 [Architecture Deep Dive](docs/architecture.md): Component diagrams, sequence flows, and database schemas.
- 🔬 [Methodology & Limitations](docs/methodology.md): Detailed problem formulation, taxonomy definitions, and edge cases.
- 🔒 [Data Governance Policy](docs/data-governance.md): Anonymization, PII redaction, and annotator well-being protocols.
- 📄 [ACL Research Paper Outline](docs/research-paper-outline.md): Academic paper structure, experimental protocols, and results tracking.
- 🧠 [Machine Learning Strategy](ml/README.md): Model selection, training pipelines, and evaluation protocols.

---

## 🤝 Contributing

We welcome contributions from researchers, engineers, and ethicists. To contribute:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/narrative-clustering-enhancement`.
3. Ensure all tests and linting pass (`ruff check .`, `npm run lint`).
4. Commit your changes: `git commit -m "Add HNSW index optimization for cross-lingual clustering"`.
5. Push to the branch: `git push origin feature/narrative-clustering-enhancement`.
6. Open a Pull Request detailing your modifications and methodology.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## ⚠️ Disclaimer & Ethical Notice

> **Important**: This software is developed for computational linguistics research, safety analysis, and defensive content moderation. Datasets and evaluation pipelines in this project may contain offensive, profane, or hateful language strictly for the purpose of benchmark evaluation and mitigation research. The developers strictly oppose hate speech, harassment, and discrimination in all forms. NarrativeLens AI is designed to assist human moderators and must not be used as an unchecked, fully autonomous censorship system.
