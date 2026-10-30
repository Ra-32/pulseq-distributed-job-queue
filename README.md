# PulseQ — Distributed Background Job Processing Platform

PulseQ is a portfolio-grade reference implementation of a background job platform. It accepts work over an HTTP API, stores job state in PostgreSQL, dispatches work through Redis Streams, and lets independently scalable worker processes execute jobs.

> **Important:** This is an educational, single-node Docker Compose deployment. It demonstrates production-relevant patterns, but it is not a managed, multi-region production service. Review the limitations and hardening checklist in `ARCHITECTURE.md` before real deployment.

## Real-world problem

Applications often need to perform slow or unreliable work (emails, invoices, report generation, image processing, webhooks) without making the user's HTTP request wait. Direct synchronous execution couples request latency to downstream services and makes transient failures difficult to recover from.

PulseQ separates request acceptance from task execution:
1. The API validates and persists a job.
2. Redis Streams carries the job to worker consumers.
3. Workers execute jobs independently.
4. PostgreSQL records lifecycle state and attempts.
5. Failed work is retried with exponential backoff and eventually sent to a dead-letter stream.
6. The dashboard shows job state and queue metrics.

## Architecture at a glance

```text
 React Dashboard
       |
       | HTTP / JSON
       v
 FastAPI API  --------------------> PostgreSQL
       |                              (job state)
       |
       v
 Redis Streams <---------------- Worker processes
 (dispatch)                          |  |  |
                                     v  v  v
                                Job handlers
                                     |
                              retry / DLQ streams
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for component responsibilities, data flow, reliability choices, scaling, trade-offs, and production hardening.

## Technology choices

| Layer | Technology | Why |
|---|---|---|
| API | Python, FastAPI | Typed REST API, validation, OpenAPI docs |
| Queue / broker | Redis Streams | Consumer groups, acknowledgements, pending entries |
| Durable job state | PostgreSQL | Queryable lifecycle state and history |
| Workers | Python processes | Scale execution separately from API |
| Frontend | React + Vite | Interactive operations dashboard |
| Local environment | Docker Compose | Repeatable multi-service development |
| Tests | pytest | API and business-logic checks |

## Quick start — Docker Compose (recommended)

Requirements: Docker Desktop / Docker Engine with Compose.

```bash
docker compose up --build
```

Open:
- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

The Compose stack starts PostgreSQL, Redis, the API, two worker replicas (defined as separate services), and the frontend.

Try creating a job:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-change-me" \
  -H "Idempotency-Key: demo-order-1001-email" \
  -d '{"task_type":"send_email","payload":{"to":"demo@example.com","subject":"Order confirmed"},"priority":5,"max_attempts":3}'
```

Then list jobs:

```bash
curl http://localhost:8000/jobs -H "X-API-Key: dev-secret-change-me"
```

Try a failing job to observe retries and dead-letter handling:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-change-me" \
  -d '{"task_type":"demo_fail","payload":{"message":"intentional demo failure"},"max_attempts":2}'
```

The demo handlers are intentionally local and do not send real email or access external services.

## Run locally with `uv` (without Docker for Python services)

You still need reachable PostgreSQL and Redis instances. Start only those dependencies:

```bash
docker compose up -d postgres redis
```

Install `uv` if needed:

```bash
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

From the project root:

```bash
uv venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
uv pip install -r requirements.txt
```

Copy environment template and adjust values if necessary:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Run API (terminal 1):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run a worker (terminal 2):

```bash
python -m app.worker
```

Run another worker in a third terminal to demonstrate horizontal worker scaling:

```bash
python -m app.worker
```

Run frontend (terminal 4):

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

See `.env.example`. Never commit real credentials. The included API key is for local development only. The current starter retries immediately; delayed exponential backoff and priority-aware dispatch are future milestones.

## Tests

Start PostgreSQL and Redis first, then:

```bash
uv pip install -r requirements.txt
pytest -q
```

The unit tests cover retry backoff and job validation. API integration tests use the configured database and Redis, so use a dedicated test database/Redis instance before running them if you add integration tests.

## Project structure

```text
pulseq/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── queue.py
│   ├── security.py
│   ├── main.py
│   ├── worker.py
│   └── handlers.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── style.css
├── tests/
│   ├── test_logic.py
│   └── test_schemas.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── ARCHITECTURE.md
└── README.md
```

## What makes this a strong SDE project?

- Separates API and worker execution so they can scale independently.
- Uses a message broker rather than blocking HTTP requests.
- Demonstrates at-least-once delivery semantics and idempotent job submission.
- Models retries, backoff, worker heartbeats, and dead-letter handling.
- Uses persistent job state, API validation, containerization, and automated tests.
- Makes trade-offs measurable: compare latency and throughput with one versus multiple workers.

The project is not claiming a novel invention. Its value is that you independently designed and implemented an integrated system, then can explain its reliability and scaling trade-offs.

## Current limitations and next engineering milestones

This starter is a strong foundation, not a finished production queue product. Before production use, implement and validate:
- Transactional outbox (to close the database-commit / Redis-publish dual-write gap).
- Scheduled-job promotion service (the API records `scheduled_for`; this starter publishes jobs immediately).
- Redis pending-entry reclaim and stale-job recovery policy.
- Per-tenant quotas, rate limiting, RBAC, audit logs, and secret rotation.
- Schema migrations with Alembic, structured logs, tracing, and alerting.
- TLS, network isolation, backup/restore, load tests, and multi-node failure tests.

Do not claim these unfinished capabilities in an interview.
