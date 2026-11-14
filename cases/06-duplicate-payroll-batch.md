# Case 6: a slow payroll service receives the same export twice

Layer: networking and external integration
Seed commit: `3405f79`  Fix commit: `e464c8c`

A reproduced failure in a lab app, written up like an incident. The "payroll service" is a local stub (`api/app/integrations/payroll_stub.py`) that behaves the way a well-run payroll API does: it honours `Idempotency-Key`.

## Symptom

A manager clicks "Export done shifts to payroll" while payroll is slow. The app reports success, but payroll shows two batches for the same shifts.

## Reproduction

```
make prove CASE=6
```

## Trace

The stub processes the first request and then stalls past the client timeout (a lost acknowledgement). The client has a 0.3 s timeout and three attempts. Trace run on the seed commit and on the fix commit:

```
seed:
   368ms HTTP Request: POST http://payroll/payroll/batches "HTTP/1.0 200 OK"
batch: batch-2
stub saw 2 requests and created 2 batch(es): ['batch-1', 'batch-2']

fix:
   370ms HTTP Request: POST http://payroll/payroll/batches "HTTP/1.0 200 OK"
batch: batch-1
stub saw 2 requests and created 1 batch(es): ['batch-1']
```

1. Browser: `POST /teams/1/exports`.
2. Route: manager check, then `run_export` writes a `payroll_exports` row (`pending`) and commits, so a crash leaves evidence.
3. `HttpPayrollClient.submit(export.id, payload)` posts to payroll. Attempt 1 is processed by payroll (`batch-1`) but the response arrives after the 0.3 s read timeout.
4. The client retries after backoff. On the seed commit the retry carries no idempotency key, so payroll cannot tell it is the same export and creates `batch-2`. On the fix commit the retry carries `Idempotency-Key: <export id>`, and payroll answers with `batch-1`.
5. Route marks the export `sent` and returns 201.

## Root cause

Retrying a non-idempotent POST after a timeout without a stable idempotency key. A timeout does not mean the request failed; it means the caller does not know. The seed commit dropped the header in a refactor, and the unit test that asserted the header was edited to match, so the suite stayed green.

## Fix

`e464c8c`: every attempt sends `Idempotency-Key: <export id>`, the same value across retries and across a later manual retry of the same export. The header assertion is back in `test_http_client_retries_5xx_with_exponential_backoff`. The client keeps its existing bounds: per-phase timeout, three attempts, exponential backoff with jitter, no retry on 4xx.

## Regression test

`api/tests/test_payroll_integration.py::test_lost_acknowledgement_does_not_create_a_second_payroll_batch`

It runs the real client over real HTTP against the stub, through the real route. A second test in the file covers a service that hangs: the route answers 502 in under two seconds and the export row is recorded as `failed`.

## Review notes

Wrong fix 1: remove the retry. That trades duplicates for lost exports whenever payroll blinks. Wrong fix 2: keep retrying but generate a fresh UUID per attempt; it looks like "adding an idempotency key" and does nothing, because the key must be stable across attempts. Wrong fix 3: raise the timeout. A longer timeout reduces how often the window opens, and a hung service still ties up a worker. Wrong fix 4: dedupe on the client by hashing the payload. That breaks when the payload legitimately repeats (same shifts, next pay period) and does nothing when the second attempt comes from another process. Also look at how a failing test got edited: a patch that loosens an existing assertion to go green is a review finding in itself.
