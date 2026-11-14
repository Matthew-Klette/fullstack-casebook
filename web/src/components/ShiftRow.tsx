import { useState } from "react";
import { ApiError, type Member, type Shift } from "../api/client";
import { useDeleteShift, useUpdateShift } from "../api/hooks";

const fmt = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export function ShiftRow({ shift, members, canDelete }: { shift: Shift; members: Member[]; canDelete: boolean }) {
  const update = useUpdateShift(shift.team_id);
  const remove = useDeleteShift(shift.team_id);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(shift.title);

  const patch = (body: Omit<Parameters<typeof update.mutate>[0]["body"], "version">) =>
    update.mutate({ id: shift.id, body: { ...body, version: shift.version } });

  const conflict = update.error instanceof ApiError && update.error.isConflict;
  const done = shift.status === "done";

  return (
    <li className={done ? "shift done" : "shift"}>
      <div className="shift-main">
        {editing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              patch({ title });
              setEditing(false);
            }}
          >
            <input aria-label="Shift title" value={title} onChange={(e) => setTitle(e.target.value)} />
            <button type="submit">Save</button>
          </form>
        ) : (
          <strong>{shift.title}</strong>
        )}
        <span className="muted">{fmt.format(new Date(shift.starts_at))}</span>
      </div>
      <select
        aria-label={`Assignee for ${shift.title}`}
        value={shift.assignee_id ?? ""}
        onChange={(e) => (e.target.value ? patch({ assignee_id: Number(e.target.value) }) : patch({ clear_assignee: true }))}
      >
        <option value="">Unassigned</option>
        {members.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name}
          </option>
        ))}
      </select>
      <span className={done ? "badge done" : "badge"}>{done ? "Done" : "Open"}</span>
      <div className="actions">
        <button onClick={() => patch({ status: done ? "open" : "done" })} disabled={update.isPending}>
          {done ? "Reopen" : "Mark done"}
        </button>
        <button onClick={() => setEditing((v) => !v)}>{editing ? "Cancel" : "Edit"}</button>
        {canDelete && (
          <button className="danger" onClick={() => remove.mutate(shift.id)}>
            Delete
          </button>
        )}
      </div>
      {conflict && (
        <p role="alert" className="error">
          Someone else changed this shift first. The latest version is shown; try your edit again.
        </p>
      )}
    </li>
  );
}
