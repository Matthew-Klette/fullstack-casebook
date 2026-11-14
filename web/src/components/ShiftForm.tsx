import { useState, type FormEvent } from "react";
import { useCreateShift } from "../api/hooks";

export function ShiftForm({ teamId }: { teamId: number }) {
  const create = useCreateShift(teamId);
  const [title, setTitle] = useState("");
  const [startsAt, setStartsAt] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { title, starts_at: new Date(startsAt).toISOString() },
      {
        onSuccess: () => {
          setTitle("");
          setStartsAt("");
        },
      },
    );
  };

  return (
    <form className="new-shift" onSubmit={submit}>
      <input aria-label="New shift title" placeholder="New shift" value={title} onChange={(e) => setTitle(e.target.value)} required />
      <input aria-label="Starts at" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required />
      <button type="submit" disabled={create.isPending}>
        Add shift
      </button>
    </form>
  );
}
