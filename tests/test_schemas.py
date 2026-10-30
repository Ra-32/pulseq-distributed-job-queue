from app.schemas import JobCreate

def test_payload_can_be_nested_json():
    request = JobCreate(task_type="generate_report",
                        payload={"filters": {"region": "west"}, "format": "csv"})
    assert request.payload["filters"]["region"] == "west"
