// Single habit card — shows name, type, target, streak, color, actions

import type { Habit } from "@/types/habit";
import { Trash2 } from "lucide-react";

interface HabitCardProps {
  habit: Habit;
  onDelete: (id: string) => void;
}

export default function HabitCard({ habit, onDelete }: HabitCardProps) {
  return (
    <div className="bg-white rounded-xl border p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span
            className="text-2xl w-10 h-10 flex items-center justify-center rounded-lg"
            style={{ backgroundColor: habit.color + "20" }}
          >
            {habit.icon}
          </span>
          <div>
            <h3 className="font-semibold text-gray-900">{habit.name}</h3>
            <p className="text-sm text-gray-500">
              {habit.habit_type === "numeric" && `Target: ${habit.target_value} ${habit.unit}`}
              {habit.habit_type === "boolean" && "Yes / No"}
              {habit.habit_type === "scale" && "Scale 1–10"}
            </p>
          </div>
        </div>
        <button
          onClick={() => onDelete(habit.id)}
          className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded"
          aria-label={`Archive ${habit.name}`}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span
          className="inline-block w-3 h-3 rounded-full"
          style={{ backgroundColor: habit.color }}
        />
        <span className="text-xs text-gray-400 capitalize">{habit.habit_type}</span>
      </div>
    </div>
  );
}
