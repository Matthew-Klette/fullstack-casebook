# Case 2: blank page after the API renamed a field

Layer: API contract between FastAPI and the web client
Seed commit: `5a34593`  Fix commit: `877338c`

A reproduced failure in a lab app, written up like an incident.

## Symptom

After a backend deploy the board shows nothing at all. No error message, no spinner: a white page. The API itself answers 200 for every request.

## Reproduction

```
make prove CASE=2
```

To see the browser failure, check out the seed commit, start the API and the Vite dev server (`make dev`), sign in as `ana@example.test` / `shiftboard-demo`, and open the browser console.

## Trace

1. `ShiftOut` in `api/app/schemas.py` now declares `start_at: datetime = Field(validation_alias="starts_at")`. The ORM attribute is still `starts_at`, so serialisation works and every backend test passes.
2. Response on the seed commit (curl against `/teams/1/shifts`, trimmed):

```
{"id": 1, "team_id": 1, "title": "Prep: sauces and stocks", "notes": "",
 "start_at": "2026-11-15T11:00:00Z", "status": "open", ...}
```

3. The browser fetches the list, TanStack Query caches it as `Shift[]`. The generated types in `web/src/api/schema.d.ts` were not regenerated, so TypeScript still believes the field is `starts_at`. `tsc` is green.
4. `ShiftRow` calls `fmt.format(new Date(shift.starts_at))`. `shift.starts_at` is `undefined`, `new Date(undefined)` is an invalid date, and `Intl.DateTimeFormat#format` throws on it. React unmounts the tree because nothing catches the render error.

Captured in headless Chromium against the seed commit:

```
HTTP 200 http://127.0.0.1:5175/api/teams/1/shifts
PAGEERROR Invalid time value
PAGEERROR Invalid time value
... (nine in total, one per shift row render attempt)
VISIBLE TEXT: ""
```

## Root cause

A breaking wire change with no gate. The committed `api/openapi.json` and the generated `web/src/api/schema.d.ts` are the contract, but nothing compared them with the running app, so the backend and the web client could drift apart without any red check. A rename is a breaking change for every consumer; here it was made as if it were internal.

## Fix

`877338c`:

- reverts the rename (a deliberate rename should be additive first: serve both names, migrate the client, then remove the old one);
- adds `api/tests/test_contract.py`, which fails with a unified diff when the live OpenAPI document differs from `api/openapi.json`, and pins the shift field set;
- adds `web/src/contract.test.ts`, which fails when `schema.d.ts` is not exactly what `api/openapi.json` generates.

When someone does change the API on purpose, `make types` regenerates both files and `tsc` then lists every call site the change breaks, before any browser sees it.

Failure message on the seed commit:

```
E         -            "title": "Starts At",
E         +            "title": "Start At",
...
E         -          "starts_at",
E         +          "start_at",
```

## Regression test

`api/tests/test_contract.py::test_committed_openapi_matches_the_running_app`

The test did not exist on the seed commit. The proof script copies it over the seed tree, which is the honest way to say "this is the check that would have caught it".

## Review notes

The plausible-but-wrong fix is to run `make types` and update `shift.starts_at` to `shift.start_at` in the web code. Everything goes green and the page renders, but any other consumer of the API (a mobile client, a payroll script, a cached older web bundle still in a user's browser during the deploy) breaks exactly as before. Ask whether the change is backward compatible and who else reads this field. The other trap is making `starts_at` optional in the web type to stop the crash: that hides the contract break and shows "Invalid Date" instead of a failure.
