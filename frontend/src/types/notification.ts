// ============================================================================
// Notification Types
// ============================================================================

export interface NotificationSettings {
  id: string;
  daily_reminder: boolean;
  weekly_report: boolean;
  streak_alerts: boolean;
  reminder_time: string;    // "HH:MM"
  created_at: string;
}

export interface NotificationSettingsUpdate {
  daily_reminder?: boolean;
  weekly_report?: boolean;
  streak_alerts?: boolean;
  reminder_time?: string;
}
