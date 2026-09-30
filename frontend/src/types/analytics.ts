// ============================================================================
// Analytics Types — mirrors backend analytics schemas
// ============================================================================

export interface DashboardData {
  today_logged: number;
  today_total: number;
  today_completion_pct: number;
  total_active_habits: number;
  current_best_streak: StreakInfo | null;
  week_completion_pct: number;
}

export interface StreakInfo {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  habit_icon: string;
  current_streak: number;
  longest_streak: number;
  last_logged_date: string | null;
}

export interface AllStreaksResponse {
  streaks: StreakInfo[];
}

export interface HabitWeeklySummary {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  this_week_avg: number | null;
  last_week_avg: number | null;
  change_pct: number | null;
  this_week_count: number;
  last_week_count: number;
}

export interface WeeklySummaryResponse {
  week_start: string;
  week_end: string;
  habits: HabitWeeklySummary[];
}

export interface TrendDataPoint {
  date: string;
  value: number | null;
}

export interface HabitTrendData {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  habit_type: string;
  data_points: TrendDataPoint[];
}

export interface MonthlyTrendResponse {
  start_date: string;
  end_date: string;
  habits: HabitTrendData[];
}

export interface HabitCompletionRate {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  habit_icon: string;
  days_logged: number;
  total_days: number;
  completion_pct: number;
}

export interface CompletionRateResponse {
  period_start: string;
  period_end: string;
  habits: HabitCompletionRate[];
}

export interface CorrelationResult {
  habit_a_id: string;
  habit_a_name: string;
  habit_b_id: string;
  habit_b_name: string;
  correlation: number;
  strength: string;
  direction: string;
  data_points: number;
  insight: string;
}

export interface CorrelationResponse {
  correlations: CorrelationResult[];
}
