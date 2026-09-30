// useLog hooks — TanStack Query for daily check-ins

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { logService } from "@/services/log.service";
import type { BulkLogCreate, LogCreate, LogUpdate } from "@/types/log";

const LOGS_KEY = ["logs"];
const ANALYTICS_KEY = ["analytics"]; // Invalidate analytics when logs change

export function useLogsByDate(date: string) {
  return useQuery({
    queryKey: [...LOGS_KEY, "date", date],
    queryFn: () => logService.getLogsByDate(date),
    enabled: !!date,
  });
}

export function useLogsByRange(start: string, end: string, habitId?: string) {
  return useQuery({
    queryKey: [...LOGS_KEY, "range", start, end, habitId],
    queryFn: () => logService.getLogsByRange(start, end, habitId),
    enabled: !!start && !!end,
  });
}

export function useCreateLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LogCreate) => logService.createLog(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}

export function useBulkCreateLogs() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkLogCreate) => logService.bulkCreateLogs(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}

export function useUpdateLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LogUpdate }) =>
      logService.updateLog(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}

export function useDeleteLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => logService.deleteLog(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}
