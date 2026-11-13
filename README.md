# Multilingual Regional E-Commerce Support Assistant (Phase 2)

A full-stack, regional e-commerce customer support assistant powered by a FastAPI async backend, PostgreSQL with semantic vector retrieval, and a React 18 + TypeScript frontend. It supports seamless customer interactions in **English**, **Tamil (தமிழ் script)**, and **Tanglish (Tamil in Roman script)** with grounded retrieval-augmented generation (RAG) for store policies and a 2,000-item product catalog.

---

## Architecture & Features

- **Multilingual Support**: Real-time intent classification and grounded reply generation across English, Tamil, and Tanglish.
- **Multilingual RAG Engine**:
  - Embedded with `intfloat/multilingual-e5-small` (384-dim).
  - Dual Vector Backend: `NumpyStore` (Windows native) and `PgVectorStore` (PostgreSQL with `pgvector` extension for Linux/Docker).
  - Grounded answers for return/shipping/payment policies and product recommendations.
  - Automatic filter relaxation when strict criteria return zero matches.
- **Deterministic Handlers**: The LLM never writes or executes SQL directly. Business rules (order ownership, return windows, refund thresholds) run in strict Python code with row-level database locks (`SELECT ... FOR UPDATE`).
- **Refund Policy Engine**:
  - Orders $\le$ ₹2,000 auto-process with immediate simulated payout via `MockPaymentGateway`.
  - Orders $>$ ₹2,000 route to human supervisor approval (`pending_approval`, `requires_human=True`).
- **Explainability & Observability**: Every message interaction logs a structured trace row in PostgreSQL containing intent, language, raw router output, retrieval hits and similarity scores, tool inputs/outputs, model names, token counts, latency, and calculated costs in INR. The response returns a `sources` array displayed in the UI.
- **Production-Ready Evaluation Suite**: 60-question multilingual benchmark set, automated threshold calibration script, evaluation runner ($\ge 85\%$ accuracy targets achieved), and monthly cost projection report.

---

## Repository Structure

```
├── backend/            # FastAPI async API, Alembic migrations, database models, tests
│   ├── app/            # Main application, config, models, schemas, services, API routers
│   ├── alembic/        # Async database migrations (001 and 002)
│   ├── data/           # Policy markdown files (EN & TA) and 2,000-product catalog
│   ├── eval/           # 60-question multilingual evaluation set (questions.jsonl)
│   ├── scripts/        # Seed, product generation, ingestion, calibration, eval, and cost scripts
│   ├── tests/          # Pytest suite with real PostgreSQL test database
│   └── README.md       # Detailed backend architecture and instructions
├── frontend/           # React 18 + TypeScript + Vite web client
│   ├── src/            # Components, hooks, API client, pages, Vitest tests
│   └── README.md       # Detailed frontend architecture and instructions
├── docker-compose.yml  # Docker deployment for PostgreSQL, Backend, and Frontend
└── README.md           # This document
```

---

## Quickstart: Running with Docker (Recommended)

To run the entire full-stack application (PostgreSQL, FastAPI Backend, and React Frontend) with a single command:

```powershell
docker compose up --build
```

- **Web Frontend**: [http://localhost:5173](http://localhost:5173)
- **FastAPI API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database**: `localhost:5432` (`ecom_dev`)

To stop all services:
```powershell
docker compose down
```

---

## Alternative: Running Locally on Windows (PowerShell)

### Step 1: Ensure PostgreSQL is Running
PostgreSQL running on `127.0.0.1:5432` with databases `ecom_dev` and `ecom_test`.

### Step 2: Start the Backend (Terminal 1)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
python scripts/seed.py
python scripts/generate_products.py
python scripts/ingest_policy.py
python scripts/ingest_products.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 3: Start the Frontend (Terminal 2)
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Verification & Test Results

### 1. Backend Pytest Suite
```powershell
cd backend
pytest -v
```
**Result**: 25 passed, 3 skipped (100% green).

### 2. Backend Evaluation Benchmark (60 Questions)
```powershell
cd backend
python -m scripts.run_eval --mock
```
- Intent Classification Accuracy: **100.0%** (Target: $\ge$ 85%)
- Expected Behavior Accuracy: **100.0%** (Target: $\ge$ 85%)
- Retrieval Hit@K Accuracy: **96.43%** (Target: $\ge$ 85%)
- Must-Contain Pass Rate: **100.0%** (Target: $\ge$ 85%)

### 3. Frontend Test Suite & Lint
```powershell
cd frontend
npm test
npm run lint
npm run build
```
**Result**: 11 passed (100% green), ESLint clean (0 errors), TypeScript build clean.
