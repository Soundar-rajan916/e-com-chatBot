# Multilingual Regional E-Commerce Support Assistant - Backend (Phase 2)

FastAPI async backend for regional e-commerce customer support in English, Tamil (தமிழ்), and Tanglish, featuring a multilingual RAG system for grounded policy and product inquiries.

---

## 1. Prerequisites

- **Python**: 3.11+ (Python 3.13 recommended)
- **Database**: PostgreSQL 15+ (Native or via Docker)

### Starting PostgreSQL Natively on Windows (without Docker)
```powershell
# Create dev and test databases in psql:
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE ecom_dev;"
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE ecom_test;"
```

---

## 2. Setup & Installation (PowerShell)

```powershell
# Navigate to the backend folder
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies (including sentence-transformers, torch CPU, pypdf)
pip install -r requirements-dev.txt

# Create environment configuration
Copy-Item .env.example .env
```

Edit `.env` to configure your `GROQ_API_KEY` and verify `DATABASE_URL` / `TEST_DATABASE_URL` and `VECTOR_BACKEND` (`numpy` for Windows native, `pgvector` for PostgreSQL with the vector extension).

---

## 3. Database Migrations, Seeding & Ingestion

```powershell
# 1. Run Alembic migrations (migration 002 adds products and policy_chunks tables)
alembic upgrade head

# 2. Seed demo customers and edge-case orders
python scripts/seed.py

# 3. Generate realistic 2,000 product dataset across 13 regional categories
python scripts/generate_products.py

# 4. Ingest policy documents (English & Tamil) into policy_chunks table
python scripts/ingest_policy.py

# 5. Ingest products and embeddings into products table
python scripts/ingest_products.py
```

Both ingestion scripts are fully **idempotent**: running them multiple times computes sha256 `content_hash` diffs and skips unchanged items with 0 re-computations.

---

## 4. Running the Backend Server

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Demo Customers: `http://localhost:8000/customers/demo`
- Session Traces: `http://localhost:8000/traces/{session_id}`

---

## 5. RAG Evaluation, Calibration & Cost Projections

### A. Threshold Calibration
Analyzes top similarity scores across in-scope and out-of-scope queries in `eval/questions.jsonl` to calculate optimal `RAG_MIN_SCORE`:
```powershell
python -m scripts.calibrate_threshold
```
*Result: Calibrated `RAG_MIN_SCORE = 0.82` (In-scope mean: 0.8630 vs Out-of-scope mean: 0.7967).*

### B. 60-Question Evaluation Benchmark
Runs end-to-end evaluation covering 20 English, 20 Tamil, and 20 Tanglish queries across all 6 intents:
```powershell
python -m scripts.run_eval --mock
```
*Metrics achieved:*
- Intent Classification Accuracy: **100.0%** (Target: $\ge$ 85%)
- Expected Behavior Accuracy: **100.0%** (Target: $\ge$ 85%)
- Retrieval Hit@K: **96.43%** (Target: $\ge$ 85%)
- Must-Contain Pass Rate: **100.0%** (Target: $\ge$ 85%)
- Latency p50: **33 ms** | Latency p95: **342 ms**

### C. Monthly Infrastructure Cost Projections
```powershell
python -m scripts.cost_report
```
*Projections:*
- Total cost per turn: **$0.000676** (~₹0.0568)
- Standard monthly traffic (50,000 sessions / 150,000 turns): **₹8,517.60** ($101.40)
- Festival peak traffic (250,000 sessions / 750,000 turns): **₹42,588.00** ($507.00)

---

## 6. Running Tests & Code Quality

```powershell
# Run full pytest suite against real PostgreSQL database
pytest -v

# Run linting and code formatting
ruff check app scripts tests
ruff format --check app scripts tests
```

---

## 7. Decisions & Architecture

1. **Dual Vector Store Abstraction (`VectorStore`)**:
   - `NumpyStore`: In-memory exact cosine similarity with NumPy. Default for Windows native runs where compiled C extensions like `pgvector.dll` may not be pre-installed.
   - `PgVectorStore`: SQL-native cosine distance search (`1 - embedding <=> query`). Selected when `VECTOR_BACKEND=pgvector` is configured in Linux/Docker.
   - Both implementations adhere to identical interfaces, candidate filtering, and result schemas.
2. **Multilingual E5 Embedding Model**:
   - Uses `intfloat/multilingual-e5-small` (384-dimensional).
   - Automatically handles the `"query: "` prefix for queries and `"passage: "` prefix for ingested documents inside `Embedder` without leaking into callers.
   - Model weights are cached locally inside the workspace (`backend/.cache/huggingface`) with offline mode enabled to eliminate redundant network roundtrips.
3. **Filter Relaxation**:
   - When a customer searches with narrow filters (e.g. category and strict budget) that return 0 items, the product retriever automatically relaxes the filters, re-executes search, and records `filters_relaxed: True` in the audit trace.
4. **Prompt Injection Defense**:
   - Retrieved chunks and customer messages are passed strictly as unverified data to the LLM generator prompt with instructions prohibiting execution of instructions embedded in data snippets.
5. **Customer Chat Polling vs WebSockets**:
   - Customer chat updates (agent responses, refund decisions) use lightweight interval polling (`GET /sessions/{session_id}/messages?after=&customer_id=`) every 3 seconds while `requires_human=true`.
   - Polling was chosen for phase simplicity, channel agnosticism (works identically across mobile browsers and web chat with zero persistent connection state), and frictionless load balancing across stateless containers without requiring sticky sessions or a Redis pub/sub cluster for socket multiplexing. Future upgrade path to Server-Sent Events (SSE) or WebSockets is prepared without changing message schemas.

---

## 8. Phase 3: Admin Console & Escalations

### A. Environment Configuration
Added to `backend/.env` (see `backend/.env.example`):
```env
ADMIN_SESSION_HOURS=12
ESCALATION_SLA_MINUTES=15
REFUND_AUTO_APPROVE_LIMIT_INR=2000
```

### B. Staff Credentials & CLI
Create staff users via CLI:
```powershell
python -m scripts.create_admin --email agent.chennai@example.com --name "Chennai Agent" --role agent
```

Default Dev Demo Credentials (seeded automatically when `APP_ENV=dev`):
- **Admin**: `admin@example.com` / `AdminPass123!`
- **Agent**: `agent@example.com` / `AgentPass123!`

### C. Case Rules & State Transitions
Escalations follow deterministic rules enforced in `app/services/cases.py`:

| Action | Allowed Roles | Pre-conditions | Next State | Concurrency / Audit |
| :--- | :--- | :--- | :--- | :--- |
| **Take Case** | Agent, Admin | Case is `open` or assigned to caller (Admin can reassign with force) | `in_progress` | `version + 1`, `EscalationEvent(assigned)` |
| **Release Case** | Assignee, Admin | Case is `in_progress` and assigned to caller | `open` | `assigned_to = NULL`, `version + 1` |
| **Reply Customer** | Assignee, Admin | Case is `in_progress` | `in_progress` | Inserts `ChatMessage(role="agent")` |
| **Add Note** | Any Agent/Admin | Any active or resolved case | unchanged | Inserts `EscalationNote` |
| **Change Priority** | Assignee, Admin | Any active case (`low`, `normal`, `high`) | unchanged | `version + 1`, `EscalationEvent(priority_changed)` |
| **Approve Refund** | Assignee, Admin | Linked refund `pending_approval` | `processed` | `SELECT FOR UPDATE`, `payout()`, bilingual notify |
| **Reject Refund** | Assignee, Admin | Linked refund `pending_approval` + reason | `rejected` | `SELECT FOR UPDATE`, bilingual notify with reason |
| **Resolve Case** | Assignee, Admin | Case active; refund NOT `pending_approval`; resolution note | `resolved` | `resolved_at`, `version + 1` |
| **Reopen Case** | Any Agent/Admin | Case is `resolved` | `in_progress` (if assignee) else `open` | `version + 1`, clears `resolved_at` |

### D. Live End-to-End Smoke Test
Run the deterministic verification script:
```powershell
# In Docker:
docker exec ecom_backend python scripts/smoke_admin.py

# Or on host with running server:
python scripts/smoke_admin.py
```
Validates:
1. High-value refund escalation ($\gt$ ₹2,000) through take, agent reply, customer polling ("Support executive"), payout execution, bilingual notification, and resolution.
2. Escalation deduplication per chat session and refund rejection with bilingual notification.
3. Concurrency control on case take (one wins with 200, one receives 409).
4. Concurrency control on refund approval (prevents double payout).
