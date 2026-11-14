"""The OpenAPI document is the contract between api/ and web/.

`api/openapi.json` is committed and the web types are generated from it. If a route or schema
changes without `make types`, these tests fail before the browser does.
"""

import difflib
import json
from pathlib import Path

from scripts.dump_openapi import render

SNAPSHOT = Path(__file__).resolve().parent.parent / "openapi.json"


def test_committed_openapi_matches_the_running_app():
    live, committed = render(), SNAPSHOT.read_text()
    diff = "".join(
        difflib.unified_diff(
            committed.splitlines(True), live.splitlines(True), "openapi.json", "live app", n=1
        )
    )
    assert live == committed, (
        f"API schema changed; run `make types` and review the web diff:\n{diff}"
    )


def test_shift_wire_format_is_pinned():
    props = json.loads(SNAPSHOT.read_text())["components"]["schemas"]["ShiftOut"]["properties"]
    assert set(props) == {
        "id", "team_id", "title", "notes", "starts_at", "status",
        "assignee_id", "assignee_name", "version",
    }  # fmt: skip
