"""The payroll client against a real HTTP server (a local stub), not a mock transport."""

import time

import pytest

from app.integrations.payroll import HttpPayrollClient
from app.integrations.payroll_stub import PayrollStub
from app.models import PayrollExport
from tests.conftest import build_client, login


@pytest.fixture
def stub_factory():
    stubs: list[PayrollStub] = []

    def make(**kwargs) -> PayrollStub:
        stubs.append(PayrollStub(**kwargs).start())
        return stubs[-1]

    yield make
    for stub in stubs:
        stub.stop()


def _export_with_one_done_shift(app_client, world):
    login(app_client, "ben")
    app_client.patch(f"/shifts/{world['k_shift'].id}", json={"version": 1, "status": "done"})
    login(app_client, "ana")
    return app_client.post(f"/teams/{world['kitchen'].id}/exports")


def test_lost_acknowledgement_does_not_create_a_second_payroll_batch(tmp_path, world, stub_factory):
    # The service processes the first request, then stalls past the client timeout.
    stub = stub_factory(slow_first=0.6)
    client = HttpPayrollClient(stub.url, timeout=0.3, retries=3, backoff=0.01)
    with build_client(tmp_path, payroll=client) as app_client:
        response = _export_with_one_done_shift(app_client, world)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "sent"
    assert stub.requests == 2  # one timed out, one retry
    assert len(stub.batches) == 1, f"payroll created {len(stub.batches)} batches for one export"


def test_hung_service_fails_fast_and_the_export_is_recorded_as_failed(
    tmp_path, world, stub_factory, db
):
    stub = stub_factory(hang=True)
    client = HttpPayrollClient(stub.url, timeout=0.2, retries=2, backoff=0.01)
    with build_client(tmp_path, payroll=client) as app_client:
        started = time.monotonic()
        response = _export_with_one_done_shift(app_client, world)
        elapsed = time.monotonic() - started

    assert response.status_code == 502
    assert elapsed < 2.0
    db.expire_all()
    assert [e.status for e in db.query(PayrollExport)] == ["failed"]
