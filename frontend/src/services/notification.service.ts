import api from "./api";
import type { NotificationSettings, NotificationSettingsUpdate } from "@/types/notification";
import type { SuccessResponse } from "@/types/common";

export const notificationService = {
  async getSettings(): Promise<NotificationSettings> {
    const res = await api.get<NotificationSettings>("/notifications/settings");
    return res.data;
  },

  async updateSettings(data: NotificationSettingsUpdate): Promise<NotificationSettings> {
    const res = await api.put<NotificationSettings>("/notifications/settings", data);
    return res.data;
  },

  async sendTestEmail(): Promise<SuccessResponse> {
    const res = await api.post<SuccessResponse>("/notifications/test-email", {
      email_type: "daily_reminder",
    });
    return res.data;
  },
};
