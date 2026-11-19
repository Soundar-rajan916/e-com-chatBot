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

---

## 9. Phase 5: WhatsApp Channel Integration (OpenWA)

### Operational Risk Statement
> open-wa is unofficial. WhatsApp may ban numbers that use unofficial clients, and WhatsApp Web changes can break the library without notice. Use a DEDICATED number that is not important to the owner, only REPLY to people who message first, never send bulk or unsolicited messages, and keep the official WhatsApp Business Cloud API as the documented production upgrade path.

### Architectural Decisions
1. **Pinned OpenWA Gateway Tag**: Pinned strictly to `ghcr.io/rmyndharis/openwa:v0.27.0` (commit `d99fa201b`, released on 2026-10-31, >2 weeks old). Image runs upstream on network `http://openwa:2785`, published to host only via `127.0.0.1:2785:2785` for localhost browser pairing.
2. **Default Engine**: Uses `baileys` (WebAssembly/WebSocket stack) to avoid headless Chromium CPU/RAM bloat and memory leaks.
3. **Webhook Security & Immediate ACK**: `POST /whatsapp/openwa/webhook` computes HMAC-SHA256 over raw unparsed request bytes matching `X-OpenWA-Signature: sha256=<hex>` with `hmac.compare_digest`. Webhooks are deduplicated via `idempotencyKey` / `deliveryId` and acknowledged with HTTP 200 in <50ms.
4. **Advisory Lock Serialization**: Inbound worker serializes message handling per WhatsApp contact using PostgreSQL transaction-level locks: `SELECT pg_advisory_xact_lock(hashtext(chat_id))`.
5. **Rate Pacing & 72h Reply Guard**: Outbound worker spaces sends by 1,500ms minimum delay with 50% randomized jitter, enforcing 15 msgs/min and 250 msgs/hr caps, refusing proactive messages after 72 hours of customer silence.
6. **Typed Confirmations (`YES <code>`)**: Refunds requested over WhatsApp require typed confirmation `YES <code>` (15 min expiry) before payout or escalation creation.
7. **Identity Linking**: One-time 6-digit codes generated in Customer Account (`/account`) allow pairing phone numbers via `LINK <code>` and unlinking via `UNLINK`.
8. **Automated Smoke Verification**:
```powershell
docker exec ecom_backend python -m scripts.smoke_whatsapp
```

---

## 10. Phase 6: Name-Driven Product Image Pipeline (Pixabay & Self-Hosted WebP)

End-to-end name-driven pipeline providing verified, relevant, mostly unique product photos with dynamic SVG placeholders as fail-safe fallback.

### Architectural Decisions
1. **Name-Driven Query Writing (`ProductImagePlan`)**:
   Reads `name_en` (with category and description context) and extracts a canonical physical `item` noun phrase (e.g. `silver cufflinks`, `braided leather belt`) with marketing noise stripped. Generates 2-3 specific search queries ($\le$ 100 characters for Pixabay), `must_show`, `must_not_show`, and `people_ok`. Stored in table `product_image_plans` so re-runs cost nothing.
2. **Pixabay Official API & No Hotlinking (Self-Hosting WebP)**:
   - Configured via `IMAGE_PROVIDER=pixabay` and `PIXABAY_API_KEY`.
   - In-memory preview URLs are used temporarily for the vision check.
   - Pixabay forbids permanent hotlinking and systematic bulk downloads: only assigned winning photos are downloaded, resized using Pillow into optimized WebP formats (800px large, 400px thumb), and stored locally in `backend/media/products/`, served at `/media/products/` by FastAPI and nginx with long immutable cache headers.
   - Responses are cached on disk for at least 24 hours (`data/image_cache/`).
   - Token bucket respects the 100 requests per 60 seconds rate limit with exponential backoff on 429.
3. **Vision Model Relevance Gate (`VisionJudge`)**:
   Candidate images are audited using Groq's Vision API (`llama-3.2-11b-vision-preview` or model in `VISION_MODEL`) with strict Pydantic JSON schemas: `{shows_item, is_main_subject, matches_must_show, hits_must_not_show, brand_logo_or_readable_brand_text, watermark, person_dominant, quality, confidence, reason}`. Rejection rules enforce: item clearly visible, confidence $\ge 0.8$, quality $\ge 0.7$, zero visible brand logos or trademark text, zero stock watermarks, and no dominant persons unless `people_ok=True`. Marginal confidence goes to `needs_review`.
4. **Perceptual Deduplication (`dHash` 64-bit + Hamming Distance $\le 6$)**:
   Enforces **0 cross-item duplicate collisions** across the entire catalog and prevents near-identical duplicate photos within an item group.
5. **Deterministic Assignment & Overrides**:
   Scoped strictly to physical `item`. Verified candidates are ranked by score and assigned deterministically, capped at `IMAGE_MAX_REUSE=2`. When candidates run out, remaining products stay on the SVG placeholder (`missing`). Manual overrides in `data/image_overrides.csv` (`sku,provider_photo_id,force,notes` or `reject`) take precedence.
6. **Provider Attribution (`docs/image-licenses.md`)**:
   Complies with Pixabay terms. A visible link to Pixabay is displayed in the storefront footer and a small muted credit line ("Photo: <photographer> / Pixabay") is rendered on the Product Detail Page gated by `SHOW_IMAGE_CREDITS` (default true), localized in both English and Tamil.

### Pipeline CLI Commands
```powershell
# 1. Image audit report (CSV and Markdown)
python -m scripts.audit_images

# 2. Run query writer & generate plan with dry-run cost estimate
python -m scripts.build_product_images --dry-run

# 3. Run pipeline category-by-category (or specific SKU)
python -m scripts.build_product_images --only-category Accessories
python -m scripts.build_product_images --only-category "Formal Shirts" --max-vision-calls 30
python -m scripts.build_product_images --only-sku SKU-MW-ACC-012

# 4. Generate review HTML contact sheet and summary markdown
python -m scripts.images_review
```

### Review & Override Tooling
- **Static Review Sheet**: Open `reports/images/review.html` in any browser to inspect assigned photos, confidence, vision reasons, and items needing review.
- **Summary Metrics**: View `reports/images/summary.md` for coverage percentage, distinct image count, max reuse, and verification of 0 cross-item duplicates.
- **Manual Overrides**: Add rows to `data/image_overrides.csv`:
  ```csv
  sku,provider_photo_id,force,notes
  SKU-MW-ACC-024,123456,true,Verified cufflinks photo
  SKU-MW-BAG-001,reject,false,Visible luxury brand logo
  ```
