# Case 7: sign-in works locally and breaks when the web app moves to its own domain

Layer: deployment and configuration
Seed commit: `f0df6f6`  Fix commit: `8b5215e`

A reproduced failure in a lab app, written up like an incident.

## Symptom

In development (Vite proxy, one origin) everything works. In a split-origin deployment (web on `https://app.example.test`, API on another host) sign-in appears to succeed and the next request is a 401, in a loop. Separately, a security review finds that the API answers credentialed preflights for any origin.

## Reproduction

```
make prove CASE=7
```

By hand on the seed commit, with a split-origin configuration:

```
SHIFTBOARD_CORS_ORIGINS=https://app.example.test SHIFTBOARD_COOKIE_SAMESITE=none \
SHIFTBOARD_COOKIE_SECURE=true SHIFTBOARD_SECRET_KEY=<32+ chars> \
python -m uvicorn app.main:app_factory --factory --port 8700
```

## Trace

Captured on the seed commit with those environment variables set:

```
--- preflight from the configured web origin
HTTP/1.1 200 OK
access-control-allow-credentials: true
access-control-allow-origin: https://app.example.test

--- preflight from an unrelated origin
HTTP/1.1 200 OK
access-control-allow-credentials: true
access-control-allow-origin: https://evil.example

--- login Set-Cookie
set-cookie: access_token=...; HttpOnly; Max-Age=900; Path=/; SameSite=lax
set-cookie: refresh_token=...; HttpOnly; Max-Age=1209600; Path=/; SameSite=lax
```

1. Browser on the web origin sends `fetch(apiBase + "/auth/login", { credentials: "include" })`. Because of the `X-Requested-With` header it is preflighted.
2. CORS middleware was given `allow_origins=["*"]` with credentials on. Starlette answers by echoing whichever `Origin` it was sent, so every site is allowed to make credentialed requests.
3. The login response sets `SameSite=lax` and no `Secure`, ignoring the environment. A cross-site `fetch` does not store or send Lax cookies, so `/auth/me` arrives without a session: 401, and the client's refresh call has no refresh cookie either.

Two separate defects, both from hardcoding values that are meant to come from `Settings`.

## Root cause

Environment-specific behaviour was written into code instead of read from configuration, and nothing exercised the split-origin configuration. In a same-origin dev setup the wrong values are invisible.

## Fix

`8b5215e`: CORS origins and cookie flags come from `Settings` again. `Settings.validate()` makes the app refuse to start in combinations that are unsafe or that browsers silently reject: `SameSite=None` without `Secure`, a wildcard origin with credentials, an unknown SameSite value, and the development secret in a secure deployment.

## Regression test

`api/tests/test_deployment_config.py::test_preflight_gives_an_unlisted_origin_nothing`
`api/tests/test_deployment_config.py::test_login_cookies_follow_the_configured_samesite_and_secure_flags`

The file also checks that the configured origin gets `Access-Control-Allow-Origin` with credentials, that local development keeps Lax cookies, and that each unsafe combination stops startup. Limit: these tests inspect headers; they do not run a browser across two real origins.

## Review notes

Wrong fix 1: set `SameSite=None` always. It makes the login work cross-site and also sends the cookie on every cross-site request, which is why the `X-Requested-With` header exists and why `Secure` is required. Wrong fix 2: leave `allow_origins=["*"]` and "fix" the missing header by hand-writing `Access-Control-Allow-Origin` in a middleware. Wrong fix 3: tell users to use the same domain and close the ticket; the config bug remains. Look for config that is hardcoded, for defaults that are only safe on a laptop, and for tests that never set the production-shaped environment.
