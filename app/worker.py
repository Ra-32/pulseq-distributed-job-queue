
import json
import logging
import os
import socket
import time

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Job, utcnow
from app.queue import get_redis, ensure_group, publish_job
from app.handlers import HANDLERS


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

log = logging.getLogger("pulseq.worker")

# Connect to Redis
r = get_redis()

# Unique worker name
consumer = (
    os.getenv("WORKER_NAME", settings.worker_name)
    + "-"
    + socket.gethostname()
)


def run():
    """
    Start the background worker.

    Important:
    The API creates database tables.
    Workers only connect to the existing database.
    """

    # Create Redis consumer group if it does not exist
    ensure_group()

    # Worker heartbeat
    r.setex(
        f"pulseq:heartbeat:{consumer}",
        30,
        str(time.time())
    )

    log.info("Worker %s started", consumer)

    # Continuously listen for jobs
    while True:

        # Update worker heartbeat
        r.setex(
            f"pulseq:heartbeat:{consumer}",
            30,
            str(time.time())
        )

        # Read one job from Redis Stream
        batches = r.xreadgroup(
            settings.redis_group,
            consumer,
            {settings.redis_stream: ">"},
            count=1,
            block=settings.poll_block_ms
        )

        # Process received jobs
        for _, messages in batches:
            for message_id, fields in messages:
                process(message_id, fields)


def process(message_id: str, fields: dict):
    """
    Process an individual background job.
    """

    job_id = fields["job_id"]

    with SessionLocal() as db:

        job = db.get(Job, job_id)

        # Ignore missing or already completed jobs
        if not job or job.status in ("succeeded", "dead_letter"):
            r.xack(
                settings.redis_stream,
                settings.redis_group,
                message_id
            )
            return

        # Mark job as running
        job.status = "running"
        job.attempts += 1
        job.updated_at = utcnow()
        db.commit()

        try:
            # Find the appropriate task handler
            handler = HANDLERS[job.task_type]

            # Execute the task
            result = handler(job.payload)

            # Mark job as successful
            job.status = "succeeded"
            job.result = result
            job.last_error = None
            job.updated_at = utcnow()

            db.commit()

            # Acknowledge the Redis message
            r.xack(
                settings.redis_stream,
                settings.redis_group,
                message_id
            )

            log.info("Job %s succeeded", job_id)

        except Exception as exc:

            # Save error information
            job.last_error = str(exc)[:2000]
            job.updated_at = utcnow()

            if job.attempts < job.max_attempts:

                # Retry the failed job
                job.status = "retrying"
                db.commit()

                # Simplified immediate retry
                publish_job(
                    job.id,
                    job.task_type,
                    job.payload,
                    job.attempts
                )

                # Acknowledge the previous message
                r.xack(
                    settings.redis_stream,
                    settings.redis_group,
                    message_id
                )

                log.warning(
                    "Job %s failed; queued retry %s/%s",
                    job_id,
                    job.attempts,
                    job.max_attempts
                )

            else:

                # Move job to Dead Letter Queue
                job.status = "dead_letter"
                db.commit()

                r.xadd(
                    "pulseq:dead-letter",
                    {
                        "job_id": job.id,
                        "error": job.last_error
                    }
                )

                # Acknowledge the failed message
                r.xack(
                    settings.redis_stream,
                    settings.redis_group,
                    message_id
                )

                log.error("Job %s moved to DLQ", job_id)


if __name__ == "__main__":
    run()
