// useAnalytics hooks — TanStack Query for dashboard, streaks, charts

import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";

const ANALYTICS_KEY = ["analytics"];

export function useDashboard() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "dashboard"],
    queryFn: () => analyticsService.getDashboard(),
    staleTime: 5 * 60 * 1000, // 5 min — matches backend cache TTL
  });
}

export function useStreaks() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "streaks"],
    queryFn: () => analyticsService.getStreaks(),
    staleTime: 30 * 60 * 1000, // 30 min
  });
}

export function useWeeklySummary() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "weekly"],
    queryFn: () => analyticsService.getWeeklySummary(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useMonthlyTrend(habitId?: string, days = 30) {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "monthly", habitId, days],
    queryFn: () => analyticsService.getMonthlyTrend(habitId, days),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

export function useCompletionRate(days = 30) {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "completion", days],
    queryFn: () => analyticsService.getCompletionRate(days),
    staleTime: 30 * 60 * 1000,
  });
}

export function useCorrelations(days = 30) {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "correlations", days],
    queryFn: () => analyticsService.getCorrelations(days),
    staleTime: 60 * 60 * 1000,
  });
}
