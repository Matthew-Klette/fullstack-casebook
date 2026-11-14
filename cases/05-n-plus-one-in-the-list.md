# Case 5: the shift list gets slower with every assigned person

Layer: persistence (query shape)
Seed commit: `4c95d90`  Fix commit: `89dff6a`

A reproduced failure in a lab app, written up like an incident.

## Symptom

Loading a busy team's board takes noticeably longer than a quiet team's, and the API log shows a burst of tiny queries for one request. The JSON is correct.

## Reproduction

```
make prove CASE=5
```

## Trace

`GET /teams/1/shifts` for a team with 14 shifts and 12 distinct assignees, SQL captured on the seed commit with SQLAlchemy engine logging, grouped by statement:

```
 12 SELECT users... FROM users WHERE users.id = ?   (the signed-in user, then one per other assignee)
  1 SELECT shifts... FROM shifts WHERE shifts.team_id = ? ORDER BY shifts.starts_at, shifts.id
  1 SELECT memberships... WHERE memberships.team_id = ? AND memberships.user_id = ?
  1 HTTP 200, 14 shifts
```

1. `list_shifts` selects the shifts only.
2. `ShiftOut.model_validate(shift)` reads `shift.assignee_name`, a property that touches the `assignee` relationship.
3. The relationship is lazy, so each distinct assignee costs one extra `SELECT` (the identity map saves repeats of the same user, so it is one query per distinct person rather than one per row).

The regression test measures the same thing as a statement count:

```
assert len(grown) == len(baseline)
E   assert 29 == 4      # 26 shifts, 26 assignees: 29 statements on the seed commit; one shift costs 4
```

## Root cause

An accidental removal of `joinedload(Shift.assignee)` from the list query. Output was identical, so every functional test kept passing; only the query count changed.

## Fix

`89dff6a`: the eager load is back (a single `LEFT OUTER JOIN users`), and `tests/test_query_count.py` counts statements with a `before_cursor_execute` listener. The assertion is that the count for one assignee equals the count for twenty-five, plus a small ceiling, so the test states the property that matters (the cost does not depend on N) without pinning an exact number that every harmless change would break.

## Regression test

`api/tests/test_query_count.py::test_listing_shifts_costs_the_same_number_of_queries_for_1_or_25_assignees`

## Review notes

Wrong fix 1: cache `assignee_name` on the shift row. It removes the queries and creates a denormalisation that goes stale when someone is renamed. Wrong fix 2: add an index on `users.id`. It is the primary key; the cost is the number of round trips, not the lookup. Wrong fix 3: a Python-side loop that fetches all users once and maps them. That works but reimplements the ORM, and the next relationship gets the same bug. Wrong fix 4: raise the page size or add a cache in front of the endpoint. The review question is always "how many statements does this request run, and does it grow with the data".
