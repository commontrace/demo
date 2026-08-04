"""Smoke test for the FastAPI wrapper.

Confirms the webhook route wires HTTP through to the charge logic. The
double-charge bug itself is exercised at the unit level in test_payments.py,
which needs nothing but the standard library.

fastapi + httpx are OPTIONAL here on purpose: the demo has to run on a stock
Python with no venv and no `pip install`, so this module skips itself when
they are missing instead of failing at import and taking the whole suite down
with it. Install them (`pip install -r requirements.txt`) to exercise the HTTP
layer too.
"""

import unittest

try:
    from fastapi.testclient import TestClient

    from app.api import app
except ImportError:  # exercised whenever fastapi/httpx are absent
    TestClient = None
    app = None


@unittest.skipIf(app is None, "fastapi + httpx not installed (optional)")
class TestWebhookRoute(unittest.TestCase):
    def test_webhook_records_a_charge(self):
        client = TestClient(app)
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


if __name__ == "__main__":
    unittest.main()
