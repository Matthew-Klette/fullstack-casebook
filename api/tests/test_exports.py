import httpx
import pytest

from app.integrations.payroll import (
    FakePayrollClient,
    HttpPayrollClient,
    PayrollRejected,
    PayrollUnavailable,
)
from tests.conftest import build_client, login


def test_export_sends_done_shifts_and_records_remote_ref(tmp_path, world, db):
    fake = FakePayrollClient()
    with build_client(tmp_path, payroll=fake) as client:
        login(client, "ben")
        client.patch(f"/shifts/{world['k_shift'].id}", json={"version": 1, "status": "done"})
        assert client.post(f"/teams/{world['kitchen'].id}/exports").status_code == 403
        login(client, "ana")
        r = client.post(f"/teams/{world['kitchen'].id}/exports")
    assert r.status_code == 201
    assert r.json()["status"] == "sent" and r.json()["shift_count"] == 1
    assert fake.calls[0][1]["shifts"][0]["title"] == "Prep"


def test_export_failure_is_recorded_and_reported_as_502(tmp_path, world):
    with build_client(tmp_path, payroll=FakePayrollClient(fail_first=1)) as client:
        login(client, "ana")
        r = client.post(f"/teams/{world['kitchen'].id}/exports")
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "payroll_unavailable"


def _client(handler, retries=3):
    sleeps: list[float] = []
    c = HttpPayrollClient(
        "http://payroll.test",
        retries=retries,
        backoff=0.1,
        sleep=sleeps.append,
        transport=httpx.MockTransport(handler),
    )
    return c, sleeps


def test_http_client_retries_5xx_with_exponential_backoff():
    attempts = []

    def handler(request):
        attempts.append(request.headers["idempotency-key"])
        return (
            httpx.Response(503)
            if len(attempts) < 3
            else httpx.Response(200, json={"batch_id": "b1"})
        )

    client, sleeps = _client(handler)
    assert client.submit("exp1", {}) == "b1"
    assert attempts == ["exp1"] * 3
    assert len(sleeps) == 2 and 0.1 <= sleeps[0] < 0.13 and 0.2 <= sleeps[1] < 0.26


def test_http_client_gives_up_after_the_retry_budget():
    client, sleeps = _client(lambda r: httpx.Response(500), retries=2)
    with pytest.raises(PayrollUnavailable):
        client.submit("exp1", {})
    assert len(sleeps) == 1


def test_http_client_does_not_retry_client_errors():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(422)

    client, _ = _client(handler)
    with pytest.raises(PayrollRejected):
        client.submit("exp1", {})
    assert len(calls) == 1
