import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type ShiftCreate, type ShiftUpdate } from "./client";

export const keys = {
  me: ["me"] as const,
  members: (teamId: number) => ["teams", teamId, "members"] as const,
  shifts: (teamId: number) => ["teams", teamId, "shifts"] as const,
};

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    // A 401 is an answer ("nobody is signed in"), not a failure.
    queryFn: () =>
      api.me().catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }),
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { email: string; password: string }) => api.login(v.email, v.password),
    onSuccess: (user) => qc.setQueryData(keys.me, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
      qc.setQueryData(keys.me, null);
    },
  });
}

export function useMembers(teamId: number) {
  return useQuery({ queryKey: keys.members(teamId), queryFn: () => api.members(teamId) });
}

export function useShifts(teamId: number) {
  return useQuery({ queryKey: keys.shifts(teamId), queryFn: () => api.shifts(teamId) });
}

export function useCreateShift(teamId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ShiftCreate) => api.createShift(teamId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.shifts(teamId) }),
  });
}

export function useUpdateShift(teamId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: number; body: ShiftUpdate }) => api.updateShift(v.id, v.body),
    // A 409 means someone else saved first. Refetch so the user edits the current version.
    onSettled: (_data, error) => {
      if (!error || (error instanceof ApiError && error.isConflict)) {
        return qc.invalidateQueries({ queryKey: ["shift", teamId] });
      }
    },
  });
}

export function useDeleteShift(teamId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteShift,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.shifts(teamId) }),
  });
}

export function useExportPayroll(teamId: number) {
  return useMutation({ mutationFn: () => api.exportPayroll(teamId) });
}
