"""Smoke test for the FastAPI wrapper.

Confirms the webhook route wires HTTP through to the charge logic. Requires
`fastapi` + `httpx` (installed via requirements.txt). The double-charge bug
itself is exercised at the unit level in test_payments.py.
"""

from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_webhook_records_a_charge():
    event = {
        "id": "evt_api_1",
        "type": "charge.succeeded",
        "data": {"amount": 4200, "customer": "cus_api"},
    }
    resp = client.post("/webhooks/stripe", json=event)
    assert resp.status_code == 200
    assert resp.json() == {"received": True}

    total = client.get("/customers/cus_api/total")
    assert total.status_code == 200
    assert total.json()["total_charged"] == 4200
