// ============================================================================
// Habit Types — mirrors backend habit schemas
// ============================================================================

export type HabitType = "numeric" | "boolean" | "scale";

export interface Habit {
  id: string;
  name: string;
  habit_type: HabitType;
  unit: string;
  target_value: number | null;
  color: string;
  icon: string;
  sort_order: number;
  is_archived: boolean;
  created_at: string;
}

export interface HabitCreate {
  name: string;
  habit_type: HabitType;
  unit?: string;
  target_value?: number | null;
  color?: string;
  icon?: string;
}

export interface HabitUpdate {
  name?: string;
  unit?: string;
  target_value?: number | null;
  color?: string;
  icon?: string;
}

export interface HabitReorderRequest {
  habit_ids: string[];
}

// Predefined colors and icons for the habit creation form
export const HABIT_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
  "#EC4899", "#06B6D4", "#F97316", "#6366F1", "#14B8A6",
];

export const HABIT_ICONS = [
  "💧", "😴", "🏃", "😊", "📖", "🧘", "💊", "🥗",
  "🎯", "⭐", "💪", "🧠", "🌙", "☀️", "❤️", "🏋️",
];
