from datetime import datetime, timezone
from app.schemas import JobCreate

def test_job_create_defaults():
    job = JobCreate(task_type="send_email", payload={"to": "demo@example.com"})
    assert job.priority == 5
    assert job.max_attempts == 3
    assert job.task_type == "send_email"

def test_priority_bounds():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        JobCreate(task_type="send_email", priority=11)

def test_unknown_task_rejected():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        JobCreate(task_type="run_arbitrary_code")
