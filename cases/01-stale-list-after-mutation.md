# Case 1: the list does not change after "Mark done"

Layer: browser state (TanStack Query cache)
Seed commit: `31413c3`  Fix commit: `5aef53e`

This is a reproduced failure in a lab app, written up like an incident. It did not happen in production.

## Symptom

A manager clicks "Mark done" on a shift. The button flips to a disabled "Mark done" for a moment, then nothing changes: the row still says Open. Reloading the page shows the shift as Done, so the write worked. Switching to another browser tab and back makes the row correct a few seconds later, which is why it looked intermittent.

## Reproduction

```
make prove CASE=1
```

That checks out the seed commit in a temporary worktree, lays the fix commit's tests over it and runs the regression test. To do it by hand:

```
git worktree add ../shiftboard-case1 31413c3
cd ../shiftboard-case1 && git checkout 5aef53e -- web/src/shiftCache.test.tsx
ln -s ../../fullstack-casebook/web/node_modules web/node_modules   # or npm ci
cd web && npx vitest run src/shiftCache.test.tsx
```

## Trace

Browser to cache to HTTP and back, recorded by a probe test on the seed commit (the fake API in `web/src/test/fakeApi.ts` logs every request):

```
TRAIL      ["GET /auth/me","GET /teams/10/shifts","GET /teams/10/members","PATCH /shifts/100"]
QUERY KEYS [["me"],["teams",10,"shifts"],["teams",10,"members"]]
PATCH BODY {"status":"done","version":1}
```

1. Click handler in `ShiftRow` calls `useUpdateShift(...).mutate({ id, body: { status: "done", version: 1 } })`.
2. `PATCH /shifts/100` succeeds and the server returns the new shift (version 2).
3. `onSettled` calls `invalidateQueries({ queryKey: ["shift", teamId] })`.
4. The cache holds `["teams", 10, "shifts"]`. TanStack Query matches keys by prefix, so `["shift", 10]` matches nothing. No refetch is issued, and the list component keeps rendering the cached array with `status: "open"`.

The trail above ends at the PATCH. There is no second `GET /teams/10/shifts`.

Failing assertion on the seed commit:

```
× shift list cache after a mutation > shows the new status without a reload after Mark done
  → Unable to find an element with the text: Done.
  ❯ src/shiftCache.test.tsx:18:30
     18|     expect(await within(row).findByText("Done")).toBeInTheDocument();
```

## Root cause

A cache key that nothing subscribes to. `useShifts` reads `keys.shifts(teamId)` (`["teams", teamId, "shifts"]`) and the mutation invalidated a hand-typed `["shift", teamId]`. The existing tests passed because they only checked that the first load renders and that creating a shift works; the create hook used the right key.

## Fix

`5aef53e`: both hooks use the shared `keys.shifts(teamId)` factory, including after a 409 so the user sees the other person's version.

## Regression test

`web/src/shiftCache.test.tsx::shows the new status without a reload after Mark done`

The same file pins the request trail (`GET`, `PATCH`, `GET`) and the refetch after a 409.

## Review notes

A plausible fix that is wrong: write the PATCH response into the cache with `setQueryData` and leave the invalidation as it was. The row would update, the test above would pass, and the bug would remain. Any change that affects other rows (for example a shift moving from "open" to a "done" filter, or the server recomputing a field) would still be stale, and the dead `["shift", teamId]` key would stay in the code as a trap. The other tempting fix, `refetchInterval` or `refetchOnWindowFocus`, hides the symptom behind polling. The check for a patch like this is to ask which query key each reader subscribes to and which key each writer invalidates, and to see a test that observes the second GET.
