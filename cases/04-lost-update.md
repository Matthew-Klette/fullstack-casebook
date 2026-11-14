# Case 4: two people edit a shift and the first edit disappears

Layer: persistence (concurrent writes)
Seed commit: `ab1cdf1`  Fix commit: `f62c2fe`

A reproduced failure in a lab app, written up like an incident.

## Symptom

Ana renames a shift to "Lunch service, grill (swap with Ana)". A minute later Ben, who opened the same shift before Ana saved, renames it to "Lunch service, fryer". Ana's title is gone and nobody was told. Each person saw a success message.

## Reproduction

```
make prove CASE=4
```

By hand on the seed commit, with two sessions (ana and ben) both reading shift 2 at version 1:

```
curl -X PATCH -b jar_ana ... -d '{"version":1,"title":"Lunch service, grill (swap with Ana)"}' /shifts/2   # 200
curl -X PATCH -b jar_ben ... -d '{"version":1,"title":"Lunch service, fryer"}' /shifts/2                   # 200
```

## Trace

Captured on the seed commit:

```
A saves (version 1):           {"id":2,..."title":"Lunch service, grill (swap with Ana)",...}
B saves with the stale version 1: {"id":2,..."title":"Lunch service, fryer",...}
final:                         {"id":2,..."title":"Lunch service, fryer",...}
INFO: "PATCH /shifts/2 HTTP/1.1" 200 OK
INFO: "PATCH /shifts/2 HTTP/1.1" 200 OK
```

1. The web client sends `{ version: <the version it rendered>, title }` (`ShiftRow`).
2. `PATCH /shifts/{id}` validates `ShiftUpdate`, which requires `version`, and calls `update_shift`.
3. On the seed commit `update_shift` loads the row, assigns the fields, does `shift.version += 1` and commits. It never compares `data.version` with the stored version. Both saves are accepted; the stored version goes 1, 2, 3 and looks healthy.
4. Last writer wins.

After the fix, the second save runs this statement (captured with SQLAlchemy logging) and gets zero affected rows:

```
UPDATE shifts SET title=?, version=(shifts.version + ?) WHERE shifts.id = ? AND shifts.version = ?
SELECT shifts.version FROM shifts WHERE shifts.id = ?
HTTP 409 {'detail': {'code': 'version_conflict', 'current_version': 2}}
```

## Root cause

The version column and the request field existed, but the comparison was missing, so optimistic concurrency was only decoration. Nothing in the suite saved twice from the same starting version.

## Fix

`f62c2fe`: the compare-and-swap is part of the UPDATE (`WHERE id = ? AND version = ?`, `SET version = version + 1`). Zero rows means 409 with the current version. The web hook already refetches on a conflict and `ShiftRow` shows "Someone else changed this shift first" (see case 1 for the refetch).

## Regression test

`api/tests/test_concurrency.py::test_stale_version_is_rejected_and_nothing_is_overwritten`

The same file has a retry-with-current-version test and a threaded test where two clients save the same version at the same moment and exactly one must get 409. That test is run in a loop with the rest of the suite and was stable on SQLite; it exercises the atomicity, but it is a probabilistic check of a race, not a proof.

## Review notes

The plausible-but-wrong fix is read, compare, write:

```python
if shift.version != data.version:
    raise VersionConflict(...)
shift.title = ...
db.commit()
```

It passes the sequential regression test. Two requests that both read version 1 before either writes both pass the comparison, and the race is back. The comparison has to be inside the write (a conditional UPDATE, or `SELECT ... FOR UPDATE` on a database that has it). Another wrong fix is to widen the lock, for example a process-level `threading.Lock`: it does nothing across workers. A third is to return the merged result silently; field-level merging is a product decision and should not be hidden in a handler.
