import json
from redis import Redis
from app.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

def ensure_group():
    try:
        redis_client.xgroup_create(settings.redis_stream, settings.redis_group, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise

def publish_job(job_id: str, task_type: str, payload: dict, attempts: int = 0):
    return redis_client.xadd(settings.redis_stream, {
        "job_id": job_id,
        "task_type": task_type,
        "payload": json.dumps(payload),
        "attempt": str(attempts),
    })

def get_redis():
    return redis_client
