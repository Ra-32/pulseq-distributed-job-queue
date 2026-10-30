from collections import Counter
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.database import Base, engine, get_db
from app.models import Job, utcnow
from app.schemas import JobCreate, JobOut, MetricsOut
from app.security import require_api_key
from app.queue import publish_job, get_redis, ensure_group

app = FastAPI(title="PulseQ API", version="1.0.0",
              description="Distributed background job processing demo")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    ensure_group()

@app.get("/health")
def health():
    try:
        get_redis().ping()
        return {"status": "ok", "redis": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")

@app.post("/jobs", response_model=JobOut, dependencies=[Depends(require_api_key)], status_code=201)
def create_job(body: JobCreate, db: Session = Depends(get_db),
               idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if idempotency_key:
        existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
        if existing:
            return existing
    job = Job(task_type=body.task_type, payload=body.payload, priority=body.priority,
              max_attempts=body.max_attempts, idempotency_key=idempotency_key)
    db.add(job)
    db.commit()
    db.refresh(job)
    # Educational simplification: DB and Redis are separate writes.
    # Use a transactional outbox for production-grade atomic publishing.
    publish_job(job.id, job.task_type, job.payload)
    return job

@app.get("/jobs", response_model=list[JobOut], dependencies=[Depends(require_api_key)])
def list_jobs(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return list(db.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit)))

@app.get("/jobs/{job_id}", response_model=JobOut, dependencies=[Depends(require_api_key)])
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/metrics", response_model=MetricsOut, dependencies=[Depends(require_api_key)])
def metrics(db: Session = Depends(get_db)):
    rows = db.execute(select(Job.status, func.count()).group_by(Job.status)).all()
    counts = {status: count for status, count in rows}
    return MetricsOut(total=sum(counts.values()), queued=counts.get("queued", 0),
        running=counts.get("running", 0), succeeded=counts.get("succeeded", 0),
        retrying=counts.get("retrying", 0), dead_letter=counts.get("dead_letter", 0))
