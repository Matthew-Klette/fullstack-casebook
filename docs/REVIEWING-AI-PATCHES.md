# Reviewing AI-generated full-stack patches

A generated patch is usually well formed, passes the tests that already exist, and is confident. The failure modes are in what it does not touch. This checklist is what I run through before accepting one. Each item points to the case in this repository where the failure was reproduced.

## 0. Before reading the diff

- What was the request, in one sentence? Does the patch do that and nothing else?
- Which layers does it touch: browser state, HTTP contract, route, service, database, external call, configuration? A patch for a "UI bug" that edits a route deserves a second look.
- Run the new tests against the old code. A test that passes without the fix proves nothing (see item 12).

## 1. Contract drift (case 2)

- Does any request or response shape change (names, nullability, enums, status codes)? Is the change backward compatible for every consumer, including older cached bundles?
- Were `api/openapi.json` and the generated types regenerated, and did `tsc` pass without casts or `any` that make the type error go away?
- Is a field made optional on the client just to stop a crash? That hides the break.

## 2. Authorization and authentication (case 3)

- For every new or changed route: who may call it, and where in the code is that enforced? Is the check in a shared lookup or only in this handler?
- Is any id taken from the request (path, query, body) and used to load a row without scoping it to the caller?
- Are 403 and 404 chosen deliberately? Does the status leak that a row exists?
- Do the tests log in as a user from another team and try every verb?
- Cookies and tokens: HttpOnly, Secure, SameSite, expiry, rotation. Is anything secret logged or returned?

## 3. State and caching on the client (case 1)

- Which query key does each reader use and which key does each writer invalidate? Do they match?
- Does a patch "fix" staleness with polling, `staleTime: 0`, or a manual `setQueryData` while leaving the real invalidation wrong?
- Are loading, error, empty and conflict states handled, or only the happy path?
- Is optimistic UI rolled back when the server says no?

## 4. Persistence and concurrency (case 4)

- Can two requests write the same row? Is the guard inside the write (conditional UPDATE, unique constraint, row lock) or a read-then-check that races?
- Are multi-step writes in one transaction? What is left behind if the process dies between steps?
- Does the migration match the model change? Is it reversible, safe on a large table, and tested from an empty database?
- Is a default or backfill needed for existing rows?

## 5. Query shape and performance (case 5)

- How many statements does the request run, and does the number grow with the data? Look for relationship access inside serialisation loops.
- Is there a statement-count test, or at least a one-off check with SQL logging?
- Are new filters and orderings supported by an index? Are lists paginated or bounded?

## 6. External calls (case 6)

- Does every outbound call have a timeout? What is the worst-case time a request can hold a worker (timeout times attempts plus backoff)?
- Are retries limited to failures that are safe to retry? Is a non-idempotent POST retried without a stable idempotency key?
- Is the outcome recorded before and after the call so a crash is visible?
- Is the integration behind an interface with a fake for tests, and one test against a real socket?

## 7. Configuration and deployment (case 7)

- Is anything environment-specific hardcoded: origins, cookie flags, URLs, secrets, feature switches?
- Does the app refuse to start on an unsafe combination instead of running quietly with it?
- Does the patch work when the web app and the API are on different origins, and when TLS terminates at a proxy?

## 8. Error handling

- Are exceptions swallowed, converted to success, or logged without being raised? Look for `except Exception: pass`, a default value returned on failure, and `catch` blocks that only `console.log`.
- Do users get an actionable message, and do operators get a log line with an id they can search for?

## 9. Multi-language and dependency changes

- New dependency: maintained, licensed compatibly, needed at all? Is the version pinned or bounded?
- Code ported between languages: integer and float semantics, time zones, string encoding, null handling and error models rarely translate one to one.
- Generated code and lockfiles: is the diff what the generator would produce today?

## 10. Maintainability

- Does the patch match the conventions of the surrounding code, or introduce a second way of doing the same thing?
- Is there dead code, a comment that restates the line below it, or an abstraction with one caller?
- Can the change be explained in two sentences in a commit message? If not, it may be two changes.

## 11. Completeness

- Does it handle the unhappy paths named in the request, not only the example shown?
- Docs, types, fixtures, seed data and the OpenAPI snapshot updated where they should be?

## 12. Tests that fail without the fix

For every behavioural change, check out the parent commit, apply only the new tests, and watch them fail for the stated reason. Then confirm they pass on the patch. `make prove CASE=N` automates this for the cases here. Treat these as red flags:

- an existing assertion was loosened or deleted to make the suite pass (case 6 seeded exactly this);
- the test mocks the very thing the bug lives in;
- the test asserts that a function was called rather than what the user or the database ends up with;
- the new test passes on the old code.
