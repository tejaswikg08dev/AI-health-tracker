import api from "./api";
import type { BulkLogCreate, HabitLog, LogCreate, LogUpdate } from "@/types/log";
import type { SuccessResponse } from "@/types/common";

export const logService = {
  async createLog(data: LogCreate): Promise<HabitLog> {
    const res = await api.post<HabitLog>("/logs", data);
    return res.data;
  },

  async bulkCreateLogs(data: BulkLogCreate): Promise<HabitLog[]> {
    const res = await api.post<HabitLog[]>("/logs/bulk", data);
    return res.data;
  },

  async getLogsByDate(date: string): Promise<HabitLog[]> {
    const res = await api.get<HabitLog[]>("/logs", { params: { date } });
    return res.data;
  },

  async getLogsByRange(start: string, end: string, habitId?: string): Promise<HabitLog[]> {
    const res = await api.get<HabitLog[]>("/logs", {
      params: { start, end, habit_id: habitId },
    });
    return res.data;
  },

  async updateLog(id: string, data: LogUpdate): Promise<HabitLog> {
    const res = await api.put<HabitLog>(`/logs/${id}`, data);
    return res.data;
  },

  async deleteLog(id: string): Promise<SuccessResponse> {
    const res = await api.delete<SuccessResponse>(`/logs/${id}`);
    return res.data;
  },
};
