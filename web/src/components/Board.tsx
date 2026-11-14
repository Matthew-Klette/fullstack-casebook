import { useState } from "react";
import { ApiError, type User } from "../api/client";
import { useExportPayroll, useLogout, useMembers, useShifts } from "../api/hooks";
import { ShiftForm } from "./ShiftForm";
import { ShiftRow } from "./ShiftRow";

export function Board({ user }: { user: User }) {
  const [teamId, setTeamId] = useState(user.teams[0]?.id);
  const logout = useLogout();

  if (teamId === undefined) {
    return <main className="card">You are not a member of any team yet.</main>;
  }
  const team = user.teams.find((t) => t.id === teamId)!;

  return (
    <main className="card">
      <header className="bar">
        <h1>Shiftboard</h1>
        <label className="inline">
          Team
          <select value={teamId} onChange={(e) => setTeamId(Number(e.target.value))}>
            {user.teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <span className="muted">
          {user.name} ({team.role})
        </span>
        <button onClick={() => logout.mutate()}>Sign out</button>
      </header>
      <ShiftList key={teamId} teamId={teamId} manager={team.role === "manager"} />
    </main>
  );
}

function ShiftList({ teamId, manager }: { teamId: number; manager: boolean }) {
  const shifts = useShifts(teamId);
  const members = useMembers(teamId);
  const payroll = useExportPayroll(teamId);

  if (shifts.isPending) return <p>Loading shifts</p>;
  if (shifts.isError) return <p role="alert" className="error">Could not load shifts.</p>;

  return (
    <>
      <ul className="shifts">
        {shifts.data.map((s) => (
          <ShiftRow key={s.id} shift={s} members={members.data ?? []} canDelete={manager} />
        ))}
        {shifts.data.length === 0 && <li className="muted">No shifts yet.</li>}
      </ul>
      <ShiftForm teamId={teamId} />
      {manager && (
        <section className="export">
          <button onClick={() => payroll.mutate()} disabled={payroll.isPending}>
            Export done shifts to payroll
          </button>
          {payroll.data && (
            <span role="status">
              Sent {payroll.data.shift_count} shift(s), reference {payroll.data.remote_ref}
            </span>
          )}
          {payroll.error && (
            <span role="alert" className="error">
              {payroll.error instanceof ApiError && payroll.error.status === 502
                ? "Payroll is unavailable. Nothing was sent twice; try again shortly."
                : "Export failed."}
            </span>
          )}
        </section>
      )}
    </>
  );
}
