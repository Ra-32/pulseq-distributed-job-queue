import time

def send_email(payload: dict) -> dict:
    # Safe demo handler: it simulates delivery and does not send a real email.
    time.sleep(0.2)
    return {"message": "Email simulated", "recipient": payload.get("to", "unknown")}

def generate_report(payload: dict) -> dict:
    time.sleep(0.4)
    return {"message": "Report generated (demo)", "format": payload.get("format", "csv")}

def demo_fail(payload: dict) -> dict:
    raise RuntimeError(payload.get("message", "Intentional demo failure"))

HANDLERS = {
    "send_email": send_email,
    "generate_report": generate_report,
    "demo_fail": demo_fail,
}
