// Create/Edit habit form — name, type, unit, target, color, icon

import { useState } from "react";
import type { HabitCreate, HabitType } from "@/types/habit";
import { HABIT_COLORS, HABIT_ICONS } from "@/types/habit";

interface HabitFormProps {
  onSubmit: (data: HabitCreate) => Promise<void>;
  onCancel: () => void;
  isLoading: boolean;
}

export default function HabitForm({ onSubmit, onCancel, isLoading }: HabitFormProps) {
  const [name, setName] = useState("");
  const [habitType, setHabitType] = useState<HabitType>("numeric");
  const [unit, setUnit] = useState("");
  const [target, setTarget] = useState<string>("");
  const [color, setColor] = useState(HABIT_COLORS[0]);
  const [icon, setIcon] = useState(HABIT_ICONS[0]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      name,
      habit_type: habitType,
      unit: habitType === "numeric" ? unit : "",
      target_value: habitType === "numeric" && target ? parseFloat(target) : undefined,
      color,
      icon,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Habit Name</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100}
          placeholder="Water Intake, Sleep, Exercise..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none" />
      </div>

      {/* Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Tracking Type</label>
        <div className="flex gap-3">
          {([
            { value: "numeric" as const, label: "📊 Number", desc: "8 glasses, 7 hours" },
            { value: "boolean" as const, label: "✅ Yes/No", desc: "Did I exercise?" },
            { value: "scale" as const, label: "🎚️ Scale 1-10", desc: "Mood, energy level" },
          ]).map((t) => (
            <button key={t.value} type="button" onClick={() => setHabitType(t.value)}
              className={`flex-1 p-3 rounded-lg border text-left transition-colors ${
                habitType === t.value ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"
              }`}>
              <p className="font-medium text-sm">{t.label}</p>
              <p className="text-xs text-gray-500 mt-0.5">{t.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Unit + Target (only for numeric) */}
      {habitType === "numeric" && (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
            <input type="text" value={unit} onChange={(e) => setUnit(e.target.value)}
              placeholder="glasses, hours, steps"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Daily Target</label>
            <input type="number" value={target} onChange={(e) => setTarget(e.target.value)}
              placeholder="8" min="0" step="0.5"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none" />
          </div>
        </div>
      )}

      {/* Color Picker */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
        <div className="flex gap-2 flex-wrap">
          {HABIT_COLORS.map((c) => (
            <button key={c} type="button" onClick={() => setColor(c)}
              className={`w-8 h-8 rounded-full border-2 transition-transform ${color === c ? "border-gray-800 scale-110" : "border-transparent"}`}
              style={{ backgroundColor: c }}
              aria-label={`Select color ${c}`} />
          ))}
        </div>
      </div>

      {/* Icon Picker */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Icon</label>
        <div className="flex gap-2 flex-wrap">
          {HABIT_ICONS.map((i) => (
            <button key={i} type="button" onClick={() => setIcon(i)}
              className={`w-10 h-10 rounded-lg text-xl flex items-center justify-center transition-colors ${
                icon === i ? "bg-brand-100 ring-2 ring-brand-500" : "bg-gray-100 hover:bg-gray-200"
              }`}>
              {i}
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button type="submit" disabled={isLoading || !name}
          className="bg-brand-600 text-white px-6 py-2 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors">
          {isLoading ? "Creating..." : "Create Habit"}
        </button>
        <button type="button" onClick={onCancel}
          className="px-6 py-2 text-gray-600 hover:text-gray-900 transition-colors">
          Cancel
        </button>
      </div>
    </form>
  );
}
