# Case 3: a member can read and edit another team's shift by id

Layer: authentication and authorization (insecure direct object reference)
Seed commit: `62f4898`  Fix commit: `48d1787`

A reproduced failure in a lab app, written up like an incident.

## Symptom

A user in the Kitchen team opens `/shifts/5` (a Front of house shift) in the API and gets the title, the assignee's name and everything else. They can also change it. The web app never links to it, so nobody noticed in normal use.

## Reproduction

```
make prove CASE=3
```

By hand on the seed commit, with the demo data (`python -m app.seed`, then uvicorn), signed in as `ben@example.test` who is only in Kitchen:

```
curl -b jar -H 'X-Requested-With: shiftboard' localhost:8300/teams/2/shifts       # 404, the team route is guarded
curl -b jar -H 'X-Requested-With: shiftboard' localhost:8300/shifts/5              # 200
curl -X PATCH -b jar ... -d '{"version":1,"title":"edited by ben"}' .../shifts/5   # 200
curl -X DELETE -b jar -H 'X-Requested-With: shiftboard' .../shifts/5               # 403
```

## Trace

Output captured on the seed commit:

```
--- ben (Kitchen member only) lists Front of house team shifts
404
--- ben reads Front of house shift 5 by id
{"id":5,"team_id":2,"title":"Opening, front of house","notes":"","starts_at":"2026-11-15T12:00:00Z","status":"open","assignee_id":3,"assignee_name":"Cara Jacobs","version":1}
--- ben edits it
{"id":5,"team_id":2,"title":"edited by ben","notes":"","starts_at":"2026-11-15T12:00:00Z","status":"open","assignee_id":3,"assignee_name":"Cara Jacobs","version":2}
--- ben deletes it
403
INFO: "GET /teams/2/shifts HTTP/1.1" 404 Not Found
INFO: "GET /shifts/5 HTTP/1.1" 200 OK
INFO: "PATCH /shifts/5 HTTP/1.1" 200 OK
INFO: "DELETE /shifts/5 HTTP/1.1" 403 Forbidden
```

1. Team-scoped routes (`/teams/{id}/...`) resolve membership through the `team_membership` dependency, which is why the list is a 404.
2. `/shifts/{id}` routes have no team in the path. They call `get_shift_for_user(db, user, shift_id)`, whose docstring promised scoping.
3. On the seed commit that function runs `select(Shift).where(Shift.id == shift_id)` and never looks at the user.
4. Delete was only partly saved by accident: the route separately looks up the caller's role in the shift's team, finds none and answers 403. That also confirms to the caller that the shift exists.

## Root cause

The lookup that every id-addressed route shares stopped joining through memberships. Because authorization lived inside one helper, one edit removed it for GET, PATCH and DELETE at once. No test asked "can a user from another team reach this id".

## Fix

`48d1787`: the helper joins `memberships` on the caller again. Missing ids and other teams' ids both produce the same 404, so ids cannot be probed. The delete route now sees 404 before it reaches the role check.

## Regression test

`api/tests/test_authorization.py::test_non_member_cannot_read_a_shift_by_id`
`api/tests/test_authorization.py::test_non_member_is_rejected_on_every_shift_route` (GET, PATCH, DELETE; also asserts the row is unchanged)

The file also checks that an unknown id and another team's id are indistinguishable, that same-team access still works, and that a shift cannot be assigned to someone outside its team.

## Review notes

Wrong fix 1: add a check in the GET route only. The PATCH route is just as open, and the next id-addressed route will repeat the mistake. Authorization belongs in the single lookup, not in each handler.
Wrong fix 2: return 403 when the shift exists but belongs to another team. It looks more "correct" but turns the endpoint into an oracle for which ids exist.
Wrong fix 3: compare `shift.team_id` with the first team in the user's list, or trust a `team_id` query parameter from the client. Both are checks against input the caller controls.
A good review asks for a test that logs in as a user from a different team and tries every verb.
