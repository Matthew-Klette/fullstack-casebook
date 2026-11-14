"""Payroll export integration.

The app depends on the `PayrollClient` interface. `HttpPayrollClient` talks to the real service
with a bounded timeout and retries with exponential backoff. `FakePayrollClient` is used by tests.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx


class PayrollError(Exception):
    pass


class PayrollRejected(PayrollError):
    """The service answered 4xx. Retrying will not help."""


class PayrollUnavailable(PayrollError):
    """Timeouts, connection failures or 5xx after all retries."""


class PayrollClient(Protocol):
    def submit(self, export_id: str, payload: dict[str, Any]) -> str:
        """Send a batch. `export_id` is stable across retries. Returns the remote batch id."""
        ...


class _Retryable(Exception):
    pass


class HttpPayrollClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 2.0,
        retries: int = 3,
        backoff: float = 0.2,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self._retries = max(1, retries)
        self._backoff = backoff
        self._sleep = sleep

    def submit(self, export_id: str, payload: dict[str, Any]) -> str:
        # Same key on every attempt: if an earlier attempt was processed but its answer was lost,
        # the service returns the original result instead of creating a second batch.
        headers = {"Idempotency-Key": export_id}
        last: Exception | None = None
        for attempt in range(self._retries):
            try:
                response = self._client.post("/payroll/batches", json=payload, headers=headers)
                if response.status_code >= 500:
                    raise _Retryable(f"payroll answered {response.status_code}")
                if response.status_code >= 400:
                    raise PayrollRejected(f"payroll answered {response.status_code}")
                return str(response.json()["batch_id"])
            except (httpx.TimeoutException, httpx.TransportError, _Retryable) as exc:
                last = exc
                if attempt + 1 < self._retries:
                    delay = self._backoff * (2**attempt)
                    self._sleep(delay + random.uniform(0, delay / 4))
        raise PayrollUnavailable(str(last)) from last


class FakePayrollClient:
    """Records calls. `fail_first` makes the first N calls raise PayrollUnavailable."""

    def __init__(self, fail_first: int = 0):
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._fail_first = fail_first

    def submit(self, export_id: str, payload: dict[str, Any]) -> str:
        self.calls.append((export_id, payload))
        if len(self.calls) <= self._fail_first:
            raise PayrollUnavailable("fake outage")
        return f"fake-{export_id[:8]}"
