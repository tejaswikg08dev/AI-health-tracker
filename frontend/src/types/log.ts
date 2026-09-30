// ============================================================================
// Habit Log Types — mirrors backend log schemas
// ============================================================================

export interface HabitLog {
  id: string;
  habit_id: string;
  log_date: string;          // "2026-09-26"
  value_numeric: number | null;
  value_boolean: boolean | null;
  value_scale: number | null;
  notes: string | null;
  created_at: string;
}

export interface LogCreate {
  habit_id: string;
  log_date: string;
  value_numeric?: number | null;
  value_boolean?: boolean | null;
  value_scale?: number | null;
  notes?: string | null;
}

export interface BulkLogEntry {
  habit_id: string;
  value_numeric?: number | null;
  value_boolean?: boolean | null;
  value_scale?: number | null;
  notes?: string | null;
}

export interface BulkLogCreate {
  log_date: string;
  entries: BulkLogEntry[];
}

export interface LogUpdate {
  value_numeric?: number | null;
  value_boolean?: boolean | null;
  value_scale?: number | null;
  notes?: string | null;
}
