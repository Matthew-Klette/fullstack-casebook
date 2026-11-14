from __future__ import annotations

from sqlalchemy.orm import Session

from app.integrations.payroll import PayrollClient, PayrollError
from app.models import PayrollExport
from app.services.shifts import done_shifts


def run_export(db: Session, team_id: int, client: PayrollClient) -> PayrollExport:
    shifts = done_shifts(db, team_id)
    export = PayrollExport(team_id=team_id, shift_count=len(shifts))
    db.add(export)
    db.commit()  # persist before the network call so a crash leaves a trace
    payload = {
        "team_id": team_id,
        "shifts": [
            {
                "id": s.id,
                "title": s.title,
                "starts_at": s.starts_at.isoformat(),
                "assignee": s.assignee_name,
            }
            for s in shifts
        ],
    }
    try:
        export.remote_ref = client.submit(export.id, payload)
        export.status = "sent"
    except PayrollError:
        export.status = "failed"
    db.commit()
    db.refresh(export)
    return export
