# E-Commerce REST API

A well-structured, fully tested e-commerce REST API with semantic search powered by RAG (Retrieval-Augmented Generation).

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)
![Redis](https://img.shields.io/badge/Redis-7-DC382D)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Tests](https://img.shields.io/badge/Tests-56%20standard-brightgreen)
![RAG Tests](https://img.shields.io/badge/RAG%20Tests-9%20integration-blue)
![Coverage](https://img.shields.io/badge/Coverage-85%25-green)
![RAG](https://img.shields.io/badge/RAG-Google%20Gemini-4285F4)

---

## Features

- **Authentication** — JWT access tokens, refresh tokens stored in Redis, register/login/logout, password reset flow
- **Public catalog** — Categories, product listing, search, featured products, and offers
- **Shopping cart** — Add, update, remove items with live stock validation
- **Orders** — Checkout from cart with automatic stock reservation and order lifecycle management
- **Addresses** — Customer shipping/billing address CRUD
- **Payments** — Saved payment methods and public payment type listing
- **User profile** — View, update, and delete customer profile
- **Admin panel** — Dashboard metrics, customer management, category/product CRUD, product image upload, order status updates
- **RAG assistant** — Semantic search over products using pgvector + Google Gemini; similarity threshold filtering; category-aware embeddings (80/20 blend); stateless multi-turn conversation via `history` in the request/response
- **Rate limiting** — SlowAPI limits on sensitive auth endpoints
- **CORS** — Configurable allowed origins for browser clients
- **Migrations** — Alembic schema versioning including pgvector extension
- **Seed data** — Default roles, categories, payment types, and admin user
- **Static media** — Product images served from `/media`

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| API framework | FastAPI | 0.136.3 | HTTP API, OpenAPI docs, dependency injection |
| ASGI server | Uvicorn | 0.48.0 | Production/dev server |
| Validation | Pydantic | 2.13.4 | Request/response schemas |
| Configuration | pydantic-settings | 2.14.1 | Environment-based settings |
| ORM | SQLAlchemy | 2.0.50 | Database models and sessions |
| Migrations | Alembic | 1.18.4 | Schema migrations |
| Database | PostgreSQL | 15 | Primary data store |
| Vector search | pgvector | 0.3.6 | Cosine similarity on product embeddings |
| Cache / sessions | Redis (server 7 / client) | 8.0.0 | Refresh tokens and password-reset tokens |
| Auth | python-jose + bcrypt | 3.5.0 / 5.0.0 | JWT signing and password hashing |
| Rate limiting | SlowAPI | 0.1.9 | Per-IP limits on auth routes |
| AI / RAG | google-generativeai | 0.7.2 | Embeddings and answer generation (Gemini) |
| DB driver | psycopg2-binary | 2.9.12 | PostgreSQL connectivity |
| Containers | Docker Compose | 2.x | Local multi-service stack |
| Testing | pytest, pytest-cov, pytest-asyncio | 9.0.3 / 7.1.0 / 1.4.0 | Unit and integration tests |
| Test doubles | fakeredis | 2.36.0 | In-memory Redis for standard test suite |

---

## Architecture

The application follows a layered design: **Router → Service → Repository → Model**, with Pydantic schemas at API boundaries.

### General request flow

```
HTTP Client
    │
    ▼
FastAPI (CORS middleware, SlowAPI rate limiter)
    │
    ▼
API Router  (/api/v1/{module})
    │
    ▼
Service     (business logic)
    │
    ▼
Repository  (SQLAlchemy queries)
    │
    ├──► PostgreSQL  (persistent data, pgvector)
    └──► Redis       (refresh / reset tokens)
```

### RAG query flow

```
POST /api/v1/rag/query  { query, history[] }
    │
    ▼
Embed query (Gemini, task_type=retrieval_query)
    │
    ▼
pgvector search:  score = 1 - (embedding <=> query_vector)
    │               candidates = RAG_TOP_K × RAG_CANDIDATE_MULTIPLIER
    │               filter: score >= RAG_SIMILARITY_THRESHOLD
    │               sort desc, take RAG_TOP_K
    ▼
Build product context (enriched documents: category stats, discounts, stock)
    │
    ▼
Build prompt:  SYSTEM + Previous conversation (last 6 msgs) + Context + Question
    │
    ▼
Generate answer (Gemini)
    │
    ▼
RAGResponse { answer, sources[], query, history[] }
```

Inactive products and zero-stock items are excluded from vector retrieval. The client stores `history` and sends it on the next turn (stateless server; no Redis session for chat).

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Google AI Studio](https://aistudio.google.com/) API key (`GEMINI_API_KEY`) for RAG features
- **Python 3.11+** — only required if you run tests or Alembic locally outside Docker

---

## Getting Started

### 1. Clone and configure

```bash
git clone https://github.com/Donovan-Nudrak/E-Commerce_API_RAG.git
cd E-Commerce_API_RAG
cp .env.example .env
```

Edit `.env` and set at minimum:

- `SECRET_KEY` — long random string for JWT signing. In production (`DEBUG=false`), use a secure random value (at least 32 characters). The `.env.example` placeholder is rejected at startup and will prevent the API from running.
- `POSTGRES_PASSWORD` — database password
- `GEMINI_API_KEY` — your Gemini API key

Use `RAG_EMBEDDING_MODEL=models/gemini-embedding-001` (required format for the Gemini embedding API).

### 2. Start services

```bash
docker compose up -d --build
```

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Seed initial data

```bash
docker compose exec api python -m app.database.seed
```

### Local URLs

| Service | URL |
|---------|-----|
| API base | http://localhost:8000 |
| Health check | http://localhost:8000/ |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Media (uploads) | http://localhost:8000/media |

### Default admin credentials (seed)

```
Email:    admin@ecommerce.com
Password: admin1234
```

> These credentials are for local development only. Change them before any public deployment.

### Index RAG

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ecommerce.com","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8000/api/v1/rag/index \
  -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://localhost:8000/api/v1/rag/index/categories \
  -H "Authorization: Bearer $TOKEN"
```

---

## RAG Module

The RAG module lets customers ask natural-language questions about the catalog. Answers are grounded in retrieved product data; the model is instructed not to invent products or prices.

### Design highlights

- **Embeddings** stored on `products.embedding` (768 dimensions) via pgvector
- **Retrieval** uses cosine distance (`<=>`); similarity score = `1 - distance`
- **Filtering** drops matches below `RAG_SIMILARITY_THRESHOLD`
- **Indexing** enriches documents with category counts, discount percentages, low-stock alerts, and category price ranges
- **Category blend** — 80% product vector, 20% category vector (applied in step 2 of indexing; see below)
- **Multi-turn** — client sends `history: [{role, content}, ...]`; server returns updated `history` (stateless; no server-side chat session)

### Retrieval pipeline

```
                    ┌─────────────────────────────┐
  query embedding   │  SELECT top (K × multiplier)│
        ───────────►│  active, stock > 0,         │
                    │  embedding NOT NULL         │
                    └─────────────┬───────────────┘
                                  │
                    score = 1 - cosine_distance
                                  │
                    ┌─────────────▼───────────────┐
                    │  score >= THRESHOLD ?       │
                    │  sort by score DESC         │
                    │  take RAG_TOP_K             │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │  Build context + prompt     │
                    │  Generate with Gemini       │
                    └─────────────────────────────┘
```

### Configurable parameters

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_TOP_K` | Max products in context and `sources` | `5` |
| `RAG_SIMILARITY_THRESHOLD` | Minimum similarity score (0–1) | `0.5` |
| `RAG_CANDIDATE_MULTIPLIER` | Initial retrieval pool size = `TOP_K × multiplier` | `3` |
| `RAG_EMBEDDING_DIM` | Vector dimensions (must match model) | `768` |
| `RAG_EMBEDDING_MODEL` | Gemini embedding model | `models/gemini-embedding-001` |
| `RAG_GENERATION_MODEL` | Gemini chat model | `gemini-2.5-flash` |

### Indexing (required order)

1. **`POST /api/v1/rag/index`** (admin) — embeds all active products from enriched text documents
2. **`POST /api/v1/rag/index/categories`** (admin) — embeds per-category summaries and blends into product vectors

Example index responses:

```json
{ "indexed": 6, "errors": 0, "message": "Reindexed active products." }
```

```json
{ "categories_processed": 5, "products_updated": 6, "errors": 0 }
```

### RAG endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/rag/query` | Public | Semantic Q&A; supports multi-turn `history` |
| POST | `/api/v1/rag/index` | Admin (Bearer) | Reindex product embeddings |
| POST | `/api/v1/rag/index/categories` | Admin (Bearer) | Apply category context blend to embeddings |
| PUT | `/api/v1/rag/products/{product_id}/reindex` | Admin (Bearer) | Reindex single product embedding |

### Multi-turn conversation example

**Turn 1** — initial question:

```bash
curl -s -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what affordable products do you have?", "history": []}'
```

Example response (abbreviated structure):

```json
{
  "answer": "We have several affordable options:\n\n* **Cotton T-Shirt**: $12.50\n* **Organic Coffee 1kg**: $18.90 (24% off)\n* **Bluetooth Headphones**: $19.99 (33% off)",
  "sources": [
    {
      "id": 3,
      "name": "Cotton T-Shirt",
      "price": "12.50",
      "discount_price": null,
      "stock": 200,
      "category_name": "Clothing",
      "similarity_score": 0.745
    },
    {
      "id": 4,
      "name": "Organic Coffe 1kg",
      "price": "24.90",
      "discount_price": "18.90",
      "stock": 80,
      "category_name": "Food & Beverages",
      "similarity_score": 0.741
    }
  ],
  "query": "what affordable products do you have?",
  "history": [
    { "role": "user", "content": "what affordable products do you have?" },
    { "role": "assistant", "content": "We have several affordable options:..." }
  ]
}
```

**Turn 2** — follow-up using `history` from turn 1:

```bash
curl -s -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "do any of those have a discount?",
    "history": [
      {"role": "user", "content": "what affordable products do you have?"},
      {"role": "assistant", "content": "We have several affordable options:..."}
    ]
  }'
```

The assistant can answer in context (e.g. listing discounted items mentioned earlier). `history` grows by two messages per turn (user + assistant). Only the last **6** messages are injected into the prompt.

### Sample `RAGResponse` fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Natural-language reply from Gemini |
| `sources` | array | Retrieved products with `similarity_score` (descending) |
| `query` | string | Current user question |
| `history` | array | Full conversation state for the client to persist |

Each source includes: `id`, `name`, `price`, `discount_price`, `stock`, `category_name`, `similarity_score`.

### Reindexing after product updates

When a product is edited via `PUT /api/v1/admin/products/{id}`, its embedding is updated automatically if `GEMINI_API_KEY` is configured in the API environment. The updated embedding is a **base** product vector (without the 80/20 category blend). To restore category blending after edits, run step 2 of [Indexing (required order)](#indexing-required-order). After bulk catalog changes, run both steps there.

Manual reindex for a single product: `PUT /api/v1/rag/products/{product_id}/reindex` (admin).

### Gemini API quotas and limits

Google AI Studio free tier (reference limits, subject to change by Google): approximately **1,500 requests/day** and **15 requests/minute** for `gemini-2.5-flash`.

| Operation | Gemini requests |
|-----------|-----------------|
| `POST /api/v1/rag/query` | 2 per call (1 embedding + 1 generation) |
| Each product indexed | 1 embedding request |

The API applies rate limiting of **20 requests/minute per IP** on `POST /api/v1/rag/query`. If the Gemini quota is exceeded, the API returns **429** with a clear message. For higher traffic, consider upgrading to a paid Google AI tier.

---

## API Modules

| Prefix | Description | Auth |
|--------|-------------|------|
| `/api/v1/auth` | Register, login, logout, refresh token, me, forgot/reset password | Mixed |
| `/api/v1/categories` | List and get categories | Public |
| `/api/v1/products` | List, search, featured, offers, product detail | Public |
| `/api/v1/cart` | Cart CRUD | Customer (Bearer) |
| `/api/v1/orders` | Create from cart, list, detail, cancel | Customer (Bearer) |
| `/api/v1/addresses` | Address CRUD | Customer (Bearer) |
| `/api/v1/payments` | Saved payment methods | Customer (Bearer) |
| `/api/v1/payment-types` | List payment types | Public |
| `/api/v1/users` | Profile management | Customer (Bearer) |
| `/api/v1/admin` | Dashboard, customers, categories, products, orders | Admin (Bearer) |
| `/api/v1/rag` | Semantic search and embedding index | Public query / Admin index |

Interactive API documentation: http://localhost:8000/docs

---

## Environment Variables

### Application

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application title in OpenAPI | `Ecommerce API` |
| `APP_VERSION` | API version string | `1.0.0` |
| `DEBUG` | FastAPI debug mode | `false` |
| `SECRET_KEY` | JWT signing secret | *(required)* |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| `POSTGRES_USER` | Database user | `ecommerce` |
| `POSTGRES_PASSWORD` | Database password | *(required)* |
| `POSTGRES_DB` | Database name | `ecommerce` |
| `POSTGRES_HOST` | Database host (`postgres` in Docker) | `postgres` |
| `POSTGRES_PORT` | Database port (internal) | `5432` |
| `REDIS_HOST` | Redis host (`redis` in Docker) | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `UPLOAD_DIR` | Local folder for product images | `uploads` |
| `MEDIA_URL_PREFIX` | URL path for static files | `/media` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins; empty disables CORS | *(empty)* — `.env.example` uses `http://localhost:3000` |
| `PASSWORD_RESET_BASE_URL` | Optional base URL for reset emails | *(empty)* |

### RAG module

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | *(required for RAG)* |
| `RAG_EMBEDDING_MODEL` | Embedding model ID | `models/gemini-embedding-001` |
| `RAG_GENERATION_MODEL` | Generation model ID | `gemini-2.5-flash` |
| `RAG_EMBEDDING_DIM` | Embedding vector size | `768` |
| `RAG_COMMIT_BATCH_SIZE` | Products processed between DB commits during bulk RAG indexing | `10` |
| `RAG_TOP_K` | Products in context/sources | `5` |
| `RAG_SIMILARITY_THRESHOLD` | Minimum cosine similarity | `0.5` |
| `RAG_CANDIDATE_MULTIPLIER` | Retrieval pool multiplier | `3` |
| `RAG_GEMINI_TIMEOUT` | Timeout in seconds for Gemini embed/generate calls | `30` |
| `RAG_MAX_HISTORY` | Max messages allowed in `RAGQuery.history` (422 if exceeded) | `10` |

Copy from [`.env.example`](.env.example); never commit `.env`.

---

## Docker Commands

| Command | Description |
|---------|-------------|
| `docker compose up -d --build` | Build and start API, Postgres, Redis |
| `docker compose down` | Stop containers |
| `docker compose down -v` | Stop and remove volumes (wipes DB) |
| `docker compose logs -f api` | Follow API logs |
| `docker compose exec api alembic upgrade head` | Apply migrations |
| `docker compose exec api python -m app.database.seed` | Seed roles, categories, admin |
| `docker compose restart api` | Restart API after `.env` changes |

### Published ports (host)

| Service | Host port | Container port |
|---------|-----------|----------------|
| API (Uvicorn) | 8000 | 8000 |
| PostgreSQL (pgvector) | 5433 | 5432 |
| Redis | 6379 | 6379 |

---

## Testing

### Testing Strategy

The project uses **two separate test suites** by design. The **standard suite** runs against real PostgreSQL with the pgvector extension; RAG logic is covered by **unit tests** that mock Gemini (`tests/unit/test_rag_service.py`), so the suite is fast and does not require a `GEMINI_API_KEY`. The **RAG integration suite** uses real PostgreSQL (`test_rag`) and the **real Gemini API** to validate the full indexing and query pipeline end to end. SQLite is not supported because product embeddings use pgvector (`Vector(768)`), which requires PostgreSQL.

### Standard Suite (56 tests)

**Coverage:** authentication, users, cart, orders, products, addresses, payments, admin, and `rag_service` (unit tests with Gemini mocks).

**Requirement:** Docker running with PostgreSQL (host port **5433** locally via `docker-compose`, **5432** in CI). Redis is mocked with fakeredis. Ensure database `test` (user `test` / `test`) exists with `CREATE EXTENSION vector` before the first run.

**Local command:**

```bash
export TEST_POSTGRES_PORT=5433
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=70
```

By default, [`pytest.ini`](pytest.ini) excludes RAG integration tests (`-m "not requires_postgres"`).

### RAG Integration Suite (9 tests)

**Coverage:** full RAG pipeline with real Gemini and pgvector — index, index/categories, query, multi-turn conversation, admin auth, embedding cleanup on soft delete, and related flows ([`tests/integration/test_rag_api.py`](tests/integration/test_rag_api.py)).

**Requirements:** Docker running, `GEMINI_API_KEY` in the environment, and database `test_rag` created.

**Create `test_rag` database (first time only):**

```bash
docker compose exec postgres psql -U ecommerce -c "CREATE DATABASE test_rag;"
docker compose exec postgres psql -U ecommerce -d test_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose exec postgres psql -U ecommerce -c "CREATE USER test_rag WITH PASSWORD 'test_rag';"
docker compose exec postgres psql -U ecommerce -c "GRANT ALL ON DATABASE test_rag TO test_rag;"
```

**Local command:**

```bash
export TEST_POSTGRES_PORT=5433
export GEMINI_API_KEY=your_key_here
pytest tests/integration/test_rag_api.py -m requires_postgres -v \
  --confcutdir=tests/integration -o addopts="-v --tb=short"
```

**Without `GEMINI_API_KEY`:** tests are **skipped** locally. In **CI** (`CI=true`), they **fail** with a clear message if the GitHub secret is missing.

### CI (GitHub Actions)

Both suites run on every push and pull request to `main` and `develop`.

- PostgreSQL service image: `pgvector/pgvector:pg15`
- `GEMINI_API_KEY` must be configured as a repository secret: **Settings → Secrets and variables → Actions → New repository secret**
- Without the secret, the 9 RAG integration tests **fail** in CI (they do not pass silently)

### Test files

| File | Description |
|------|-------------|
| [`tests/conftest.py`](tests/conftest.py) | Base fixtures with PostgreSQL |
| [`tests/conftest_rag.py`](tests/conftest_rag.py) | RAG fixtures with PostgreSQL + Gemini |
| [`tests/unit/test_rag_service.py`](tests/unit/test_rag_service.py) | 11 unit tests with Gemini mocks |
| [`tests/integration/test_rag_api.py`](tests/integration/test_rag_api.py) | 9 RAG tests with real Gemini |
| [`tests/integration/test_auth_api.py`](tests/integration/test_auth_api.py) | Auth endpoints |
| [`tests/integration/test_users_api.py`](tests/integration/test_users_api.py) | User profile |
| [`tests/integration/test_cart_api.py`](tests/integration/test_cart_api.py) | Shopping cart |
| [`tests/integration/test_categories_api.py`](tests/integration/test_categories_api.py) | Categories |
| [`tests/integration/test_products_api.py`](tests/integration/test_products_api.py) | Catalog and admin CRUD |
| [`tests/integration/test_addresses_api.py`](tests/integration/test_addresses_api.py) | Shipping addresses |
| [`tests/integration/test_orders_lifecycle.py`](tests/integration/test_orders_lifecycle.py) | Full order flow |
| [`tests/integration/test_payments_api.py`](tests/integration/test_payments_api.py) | Payment methods |
| [`tests/unit/test_admin_service.py`](tests/unit/test_admin_service.py) | Admin service unit tests |

---

## Project Structure

```
E-Commerce/
├── main.py                          # FastAPI app entrypoint
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pytest.ini
├── .env.example
├── .github/workflows/ci.yml
├── alembic/
│   └── versions/
│       ├── 656bd22f17ea_initial_migration.py
│       ├── add_pgvector_to_products.py
│       └── add_indexed_at_to_products.py
├── app/
│   ├── api/v1/
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── cart/
│   │   ├── categories/
│   │   ├── products/
│   │   ├── orders/
│   │   ├── addresses/
│   │   ├── payments/
│   │   ├── payment_types/
│   │   ├── users/
│   │   └── rag/                     # RAG endpoints
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── redis.py
│   │   └── limiter.py
│   ├── database/
│   │   ├── session.py
│   │   └── seed.py
│   ├── models/
│   ├── repositories/
│   │   └── vector_repository.py     # pgvector queries
│   ├── schemas/
│   │   └── rag.py
│   ├── services/
│   │   └── rag_service.py           # RAG pipeline
│   └── utils/
└── tests/
    ├── conftest.py
    ├── conftest_rag.py
    ├── integration/
    │   └── test_rag_api.py
    └── unit/
```

---

## Order Flow

Customer orders start as **PENDING** when created from the cart. Stock is decremented at creation time. Admins advance status through valid transitions.

```
              ┌──────────┐
              │ PENDING  │
              └────┬─────┘
         ┌─────────┴─────────┐
         ▼                   ▼
    ┌─────────┐        ┌───────────┐
    │  PAID   │───────►│  SHIPPED  │───────►┌───────────┐
    └─────────┘        └───────────┘        │ DELIVERED │
         │                                  └───────────┘
         │ (customer, PENDING only)
         ▼
    ┌───────────┐
    │ CANCELLED │ → stock restored
    └───────────┘
```

**Admin API:** `PUT /api/v1/admin/orders/{order_id}/status` with body `{ "status": "PAID" }` (etc.).

Valid transitions are enforced in [`app/services/order_service.py`](app/services/order_service.py):

| From | To |
|------|-----|
| PENDING | PAID, CANCELLED |
| PAID | SHIPPED |
| SHIPPED | DELIVERED |
| DELIVERED | *(terminal)* |
| CANCELLED | *(terminal)* |

---

## Business Rules

- Only **active** products (`is_active = true`) appear in the public catalog and RAG index pool for active items
- **RAG vector search** only returns products that are active, have `stock > 0`, and a non-null `embedding`
- **Cart** rejects inactive products and quantities above available stock
- **Orders** require a non-empty cart; inactive line items block checkout
- **Stock reservation** — creating an order decrements stock immediately; cancelling a **PENDING** order restores stock
- **Pricing** — order lines use `discount_price` when set, otherwise `price`
- **Order cancel** — customers may cancel only while status is `PENDING`
- **Admin status updates** must follow `VALID_TRANSITIONS`; invalid jumps return 400
- **JWT** — protected routes require `Authorization: Bearer <access_token>`
- **Admin routes** — require role `Administrator` (seed admin or promoted user)
- **RAG index** — admin-only; returns 503 if `GEMINI_API_KEY` is missing
- **RAG multi-turn** — server stores no chat session; client must send `history` each request; prompt uses last 6 messages max
- **Product delete (admin)** — soft delete (`is_active = false`), not physical removal
- **Auth rate limits** — register, login, and forgot-password endpoints are rate-limited per IP
- **CORS** — disabled when `CORS_ALLOWED_ORIGINS` is empty (API-only mode)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
