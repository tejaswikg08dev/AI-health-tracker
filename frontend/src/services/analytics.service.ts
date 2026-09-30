import api from "./api";
import type {
  AllStreaksResponse,
  CompletionRateResponse,
  CorrelationResponse,
  DashboardData,
  MonthlyTrendResponse,
  WeeklySummaryResponse,
} from "@/types/analytics";

export const analyticsService = {
  async getDashboard(): Promise<DashboardData> {
    const res = await api.get<DashboardData>("/analytics/dashboard");
    return res.data;
  },

  async getStreaks(): Promise<AllStreaksResponse> {
    const res = await api.get<AllStreaksResponse>("/analytics/streaks");
    return res.data;
  },

  async getWeeklySummary(): Promise<WeeklySummaryResponse> {
    const res = await api.get<WeeklySummaryResponse>("/analytics/weekly-summary");
    return res.data;
  },

  async getMonthlyTrend(habitId?: string, days = 30): Promise<MonthlyTrendResponse> {
    const res = await api.get<MonthlyTrendResponse>("/analytics/monthly-trend", {
      params: { habit_id: habitId, days },
    });
    return res.data;
  },

  async getCompletionRate(days = 30): Promise<CompletionRateResponse> {
    const res = await api.get<CompletionRateResponse>("/analytics/completion-rate", {
      params: { days },
    });
    return res.data;
  },

  async getCorrelations(days = 30): Promise<CorrelationResponse> {
    const res = await api.get<CorrelationResponse>("/analytics/correlations", {
      params: { days },
    });
    return res.data;
  },
};
