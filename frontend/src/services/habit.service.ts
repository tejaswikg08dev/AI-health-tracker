import api from "./api";
import type { Habit, HabitCreate, HabitReorderRequest, HabitUpdate } from "@/types/habit";
import type { SuccessResponse } from "@/types/common";

export const habitService = {
  async getHabits(includeArchived = false): Promise<Habit[]> {
    const res = await api.get<Habit[]>("/habits", {
      params: { include_archived: includeArchived },
    });
    return res.data;
  },

  async getHabit(id: string): Promise<Habit> {
    const res = await api.get<Habit>(`/habits/${id}`);
    return res.data;
  },

  async createHabit(data: HabitCreate): Promise<Habit> {
    const res = await api.post<Habit>("/habits", data);
    return res.data;
  },

  async updateHabit(id: string, data: HabitUpdate): Promise<Habit> {
    const res = await api.put<Habit>(`/habits/${id}`, data);
    return res.data;
  },

  async deleteHabit(id: string): Promise<SuccessResponse> {
    const res = await api.delete<SuccessResponse>(`/habits/${id}`);
    return res.data;
  },

  async reorderHabits(data: HabitReorderRequest): Promise<Habit[]> {
    const res = await api.put<Habit[]>("/habits/reorder", data);
    return res.data;
  },
};
