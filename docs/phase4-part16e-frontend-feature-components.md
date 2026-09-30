# 🧩 Phase 4 Part 16e: Frontend — Feature Components

> **"Nine reusable components: HabitCard + HabitForm for CRUD, DailyCheckIn for bulk logging (numeric/boolean/scale inputs), three Recharts visualizations (bar, line, pie), and three AI chat components (window, message bubble, input)."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16d-frontend-layout-components.md](./phase4-part16d-frontend-layout-components.md) |
| **Next** | [phase4-part16f-frontend-pages.md](./phase4-part16f-frontend-pages.md) |
| **Files in This Doc** | 9 component files |
| **Time to Type** | ~50 minutes |
| **Difficulty** | Medium-Hard (Recharts data transforms, dynamic form inputs) |

---

## 1. `src/components/habits/HabitCard.tsx`

```typescript
// Single habit card — shows name, type, target, color, actions

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
```

**`style={{ backgroundColor: habit.color + "20" }}`** — Adds `20` (hex opacity ~12%) to the color. `#3B82F620` is a very light blue background behind the emoji icon. Tailwind can't do dynamic colors, so we use inline `style`.

**`onDelete: (id: string) => void`** — The parent (HabitsPage) passes the delete handler. HabitCard doesn't know HOW deletion works — it just calls the callback. This is **props down, events up** — React's core pattern.

---

## 2. `src/components/habits/HabitForm.tsx`

```typescript
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
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required
          maxLength={100} placeholder="Water Intake, Sleep, Exercise..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2
            focus:ring-brand-500 focus:border-transparent outline-none" />
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
                habitType === t.value
                  ? "border-brand-500 bg-brand-50"
                  : "border-gray-200 hover:border-gray-300"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2
                focus:ring-brand-500 focus:border-transparent outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Daily Target</label>
            <input type="number" value={target} onChange={(e) => setTarget(e.target.value)}
              placeholder="8" min="0" step="0.5"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2
                focus:ring-brand-500 focus:border-transparent outline-none" />
          </div>
        </div>
      )}

      {/* Color Picker */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
        <div className="flex gap-2 flex-wrap">
          {HABIT_COLORS.map((c) => (
            <button key={c} type="button" onClick={() => setColor(c)}
              className={`w-8 h-8 rounded-full border-2 transition-transform ${
                color === c ? "border-gray-800 scale-110" : "border-transparent"
              }`}
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
              className={`w-10 h-10 rounded-lg text-xl flex items-center justify-center
                transition-colors ${
                icon === i
                  ? "bg-brand-100 ring-2 ring-brand-500"
                  : "bg-gray-100 hover:bg-gray-200"
              }`}>
              {i}
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button type="submit" disabled={isLoading || !name}
          className="bg-brand-600 text-white px-6 py-2 rounded-lg hover:bg-brand-700
            disabled:opacity-50 transition-colors">
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
```

**Conditional rendering for numeric fields:**
```typescript
{habitType === "numeric" && (
  <div className="grid grid-cols-2 gap-4">
    {/* Unit + Target inputs */}
  </div>
)}
```
Unit and target only make sense for numeric habits. Boolean ("Did I exercise?") and scale (1-10) don't need them. The section disappears when you select a different type.

**`"numeric" as const`** — TypeScript assertion. Without it, `value` would be typed as `string`. With `as const`, it's typed as the literal `"numeric"`, which matches `HabitType`.

---

## 3. `src/components/logs/DailyCheckIn.tsx`

```typescript
// Daily check-in form — log all habits for a given date

import { useState } from "react";
import type { Habit } from "@/types/habit";
import type { HabitLog, BulkLogCreate, BulkLogEntry } from "@/types/log";
import { Save, Check } from "lucide-react";

interface DailyCheckInProps {
  habits: Habit[];
  existingLogs: HabitLog[];
  date: string;
  onSave: (data: BulkLogCreate) => Promise<unknown>;
  isSaving: boolean;
}

export default function DailyCheckIn({
  habits, existingLogs, date, onSave, isSaving
}: DailyCheckInProps) {
  // Build initial values from existing logs
  const getExistingValue = (habitId: string) => {
    const log = existingLogs.find((l) => l.habit_id === habitId);
    if (!log) return undefined;
    return {
      numeric: log.value_numeric,
      boolean: log.value_boolean,
      scale: log.value_scale,
    };
  };

  // State for each habit's value
  const [values, setValues] = useState<Record<string, {
    numeric?: number | null;
    boolean?: boolean | null;
    scale?: number | null;
  }>>(() => {
    const initial: Record<string, any> = {};
    habits.forEach((h) => {
      initial[h.id] = getExistingValue(h.id) || {};
    });
    return initial;
  });

  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    const entries: BulkLogEntry[] = habits
      .map((h) => {
        const val = values[h.id];
        if (!val) return null;
        return {
          habit_id: h.id,
          value_numeric: h.habit_type === "numeric" ? val.numeric : undefined,
          value_boolean: h.habit_type === "boolean" ? val.boolean : undefined,
          value_scale: h.habit_type === "scale" ? val.scale : undefined,
        } as BulkLogEntry;
      })
      .filter((e): e is BulkLogEntry => e !== null);

    await onSave({ log_date: date, entries });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateValue = (habitId: string, field: string, value: unknown) => {
    setValues((prev) => ({
      ...prev,
      [habitId]: { ...prev[habitId], [field]: value },
    }));
  };

  return (
    <div className="space-y-4">
      {habits.map((habit) => {
        const hasExisting = existingLogs.some((l) => l.habit_id === habit.id);
        return (
          <div key={habit.id}
            className={`bg-white rounded-xl border p-4 flex items-center gap-4 ${
              hasExisting ? "border-green-200 bg-green-50/30" : ""
            }`}>
            {/* Icon + Name */}
            <span className="text-2xl w-10 h-10 flex items-center justify-center rounded-lg"
              style={{ backgroundColor: habit.color + "20" }}>
              {habit.icon}
            </span>
            <div className="flex-1">
              <p className="font-medium text-gray-900">{habit.name}</p>
              <p className="text-xs text-gray-400">
                {habit.habit_type === "numeric" &&
                  `Target: ${habit.target_value} ${habit.unit}`}
                {habit.habit_type === "boolean" && "Yes / No"}
                {habit.habit_type === "scale" && "Rate 1–10"}
              </p>
            </div>

            {/* Input based on type */}
            <div className="w-40">
              {habit.habit_type === "numeric" && (
                <div className="flex items-center gap-2">
                  <input type="number" min="0" step="0.5"
                    value={values[habit.id]?.numeric ?? ""}
                    onChange={(e) => updateValue(habit.id, "numeric",
                      e.target.value ? parseFloat(e.target.value) : null)}
                    className="w-20 px-2 py-1.5 border border-gray-300 rounded-lg
                      text-center focus:ring-2 focus:ring-brand-500
                      focus:border-transparent outline-none"
                    placeholder="0" />
                  <span className="text-sm text-gray-500">{habit.unit}</span>
                </div>
              )}

              {habit.habit_type === "boolean" && (
                <button
                  onClick={() => updateValue(habit.id, "boolean",
                    !values[habit.id]?.boolean)}
                  className={`w-full py-2 rounded-lg font-medium text-sm transition-colors ${
                    values[habit.id]?.boolean
                      ? "bg-green-500 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}>
                  {values[habit.id]?.boolean ? "✅ Done" : "Not yet"}
                </button>
              )}

              {habit.habit_type === "scale" && (
                <div className="flex items-center gap-2">
                  <input type="range" min="1" max="10"
                    value={values[habit.id]?.scale ?? 5}
                    onChange={(e) => updateValue(habit.id, "scale",
                      parseInt(e.target.value))}
                    className="flex-1 accent-brand-500" />
                  <span className="text-lg font-bold w-8 text-center"
                    style={{ color: habit.color }}>
                    {values[habit.id]?.scale ?? 5}
                  </span>
                </div>
              )}
            </div>

            {/* Logged indicator */}
            {hasExisting && <Check className="w-5 h-5 text-green-500" />}
          </div>
        );
      })}

      {/* Save Button */}
      <button onClick={handleSave} disabled={isSaving}
        className="w-full bg-brand-600 text-white py-3 rounded-xl font-medium
          hover:bg-brand-700 disabled:opacity-50 flex items-center justify-center
          gap-2 transition-colors">
        {saved ? (
          <><Check className="w-5 h-5" /> Saved!</>
        ) : (
          <><Save className="w-5 h-5" /> {isSaving ? "Saving..." : "Save All"}</>
        )}
      </button>
    </div>
  );
}
```

**Three input types in one component:**
- **numeric** → `<input type="number">` with unit label
- **boolean** → toggle `<button>` (green "Done" / gray "Not yet")
- **scale** → `<input type="range" min="1" max="10">` with number display

**`Record<string, { ... }>`** — TypeScript utility type. A dictionary where keys are strings (habit IDs) and values are objects with numeric/boolean/scale. Like Python's `dict[str, dict]`.

---

## 4. `src/components/charts/WeeklyBarChart.tsx`

```typescript
// Weekly bar chart — this week vs last week comparison

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { HabitWeeklySummary } from "@/types/analytics";

interface WeeklyBarChartProps {
  data: HabitWeeklySummary[];
}

export default function WeeklyBarChart({ data }: WeeklyBarChartProps) {
  const chartData = data.map((h) => ({
    name: h.habit_name.length > 12 ? h.habit_name.slice(0, 12) + "…" : h.habit_name,
    "This Week": h.this_week_avg ?? 0,
    "Last Week": h.last_week_avg ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} barGap={4}>
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        <Bar dataKey="Last Week" fill="#CBD5E1" radius={[4, 4, 0, 0]} />
        <Bar dataKey="This Week" fill="#3B82F6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

**`ResponsiveContainer`** — Makes the chart resize with its parent. Without it, you'd need hardcoded pixel dimensions.

**`radius={[4, 4, 0, 0]}`** — Rounded top corners on bars (top-left, top-right, bottom-right, bottom-left).

---

## 5. `src/components/charts/MonthlyLineChart.tsx`

```typescript
// Monthly line chart — 30-day trends for all habits

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { HabitTrendData } from "@/types/analytics";

interface MonthlyLineChartProps {
  data: HabitTrendData[];
}

export default function MonthlyLineChart({ data }: MonthlyLineChartProps) {
  if (!data.length) return <p className="text-gray-500 text-center py-8">
    No trend data available.</p>;

  // Transform: pivot habit data into date-keyed rows for Recharts
  const dateMap: Record<string, Record<string, number | null>> = {};
  data.forEach((habit) => {
    habit.data_points.forEach((dp) => {
      if (!dateMap[dp.date]) dateMap[dp.date] = {};
      dateMap[dp.date][habit.habit_name] = dp.value;
    });
  });

  const chartData = Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, values]) => ({
      date: date.slice(5), // "09-26" instead of "2026-09-26"
      ...values,
    }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {data.map((habit) => (
          <Line
            key={habit.habit_id}
            type="monotone"
            dataKey={habit.habit_name}
            stroke={habit.habit_color}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Key: Data Transform (Pivot)

The API returns data per-habit:
```json
[
  { "habit_name": "Water", "data_points": [{"date": "09-25", "value": 8}, ...] },
  { "habit_name": "Sleep", "data_points": [{"date": "09-25", "value": 7}, ...] }
]
```

Recharts needs data per-date:
```json
[
  { "date": "09-25", "Water": 8, "Sleep": 7 },
  { "date": "09-26", "Water": 6, "Sleep": 8 }
]
```

The `dateMap` transform **pivots** the data from habit-first to date-first.

---

## 6. `src/components/charts/CompletionPieChart.tsx`

```typescript
// Completion pie chart — shows completion % per habit

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { HabitCompletionRate } from "@/types/analytics";

interface CompletionPieChartProps {
  data: HabitCompletionRate[];
}

export default function CompletionPieChart({ data }: CompletionPieChartProps) {
  if (!data.length) return <p className="text-gray-500 text-center py-8">
    No completion data yet.</p>;

  const chartData = data.map((h) => ({
    name: h.habit_name,
    value: h.completion_pct,
    color: h.habit_color,
    icon: h.habit_icon,
    days: `${h.days_logged}/${h.total_days} days`,
  }));

  return (
    <div className="flex flex-col lg:flex-row items-center gap-8">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
            paddingAngle={3} dataKey="value"
            label={({ name, value }) => `${name}: ${value}%`}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend with details */}
      <div className="space-y-2 min-w-[200px]">
        {chartData.map((item, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="w-3 h-3 rounded-full"
              style={{ backgroundColor: item.color }} />
            <div className="flex-1">
              <p className="text-sm font-medium">{item.icon} {item.name}</p>
              <p className="text-xs text-gray-500">
                {item.days} — {item.value.toFixed(0)}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**`innerRadius={60}`** — Makes it a **donut chart** (hollow center) instead of a solid pie. More modern look.

**`<Cell fill={entry.color} />`** — Each slice gets its own color from the habit's `color` field. Without `Cell`, all slices would be the same color.

---

## 7. `src/components/ai/ChatMessage.tsx`

```typescript
// Single chat message bubble — user (right) or assistant (left)

import type { ChatMessage } from "@/types/ai";
import { User, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export default function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
        isUser ? "bg-brand-100 text-brand-600" : "bg-gray-100 text-gray-600"
      )}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message bubble */}
      <div className={cn(
        "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
        isUser
          ? "bg-brand-600 text-white rounded-tr-md"
          : "bg-gray-100 text-gray-800 rounded-tl-md"
      )}>
        {message.content.split("\n").map((line, i) => (
          <p key={i} className={cn(i > 0 && "mt-2")}>{line}</p>
        ))}
      </div>
    </div>
  );
}
```

**`flex-row-reverse`** — User messages align right (avatar on right, bubble on left of avatar). Assistant messages use normal `flex-row` (avatar on left).

**`rounded-tr-md`** — The user's bubble has all corners rounded EXCEPT the top-right (makes it look like it's "coming from" the user avatar). This is the standard chat bubble design pattern.

---

## 8. `src/components/ai/ChatInput.tsx`

```typescript
// Chat input — text area with send button, Enter to send

import { useState } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => Promise<void>;
  isLoading: boolean;
}

export default function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isLoading) return;

    setMessage("");
    await onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Enter sends, Shift+Enter adds a new line
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit}
      className="border-t border-gray-200 p-4 flex gap-3 items-end">
      <textarea value={message} onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your health habits..."
        rows={1} disabled={isLoading}
        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl resize-none
          focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none
          disabled:opacity-50 text-sm"
        style={{ maxHeight: "120px" }} />
      <button type="submit" disabled={isLoading || !message.trim()}
        className="bg-brand-600 text-white p-2.5 rounded-xl hover:bg-brand-700
          disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
        aria-label="Send message">
        <Send className="w-5 h-5" />
      </button>
    </form>
  );
}
```

---

## 9. `src/components/ai/ChatWindow.tsx`

```typescript
// Chat window — scrollable message list with loading indicator

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/types/ai";
import ChatMessageBubble from "./ChatMessage";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import { MessageSquare } from "lucide-react";

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export default function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Empty state */}
      {messages.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center h-full text-center
          text-gray-400 py-16">
          <MessageSquare className="w-12 h-12 mb-4" />
          <p className="text-lg font-medium">Ask your AI Health Coach</p>
          <p className="text-sm mt-1 max-w-md">
            I can check your habit data, find patterns, search your documents,
            and help you build better habits.
          </p>
          <div className="flex flex-wrap gap-2 mt-6 justify-center">
            {[
              "How's my sleep this week?",
              "Am I drinking enough water?",
              "What correlates with my mood?",
              "Help me improve my exercise habit",
            ].map((q) => (
              <span key={q}
                className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full">
                {q}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      {messages.map((msg) => (
        <ChatMessageBubble key={msg.id} message={msg} />
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400 py-2">
          <LoadingSpinner size="sm" />
          <span className="text-sm">Thinking...</span>
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </div>
  );
}
```

**`useRef<HTMLDivElement>(null)` + `scrollIntoView`** — Auto-scroll pattern. `bottomRef` points to an invisible div at the bottom. Whenever `messages` changes (new message arrives), the `useEffect` scrolls that div into view. The user always sees the latest message.

---

## 10. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Props down, events up** | HabitCard → `onDelete` callback |
| 2 | **Conditional rendering by type** | DailyCheckIn → numeric/boolean/scale inputs |
| 3 | **`Record<K, V>`** | DailyCheckIn → habit ID → value mapping |
| 4 | **Data pivot transform** | MonthlyLineChart → habit-first to date-first |
| 5 | **Recharts `ResponsiveContainer`** | All charts → auto-resize |
| 6 | **Donut chart `innerRadius`** | CompletionPieChart → hollow center |
| 7 | **`flex-row-reverse`** | ChatMessage → user messages align right |
| 8 | **`useRef` + `scrollIntoView`** | ChatWindow → auto-scroll to bottom |
| 9 | **Empty state pattern** | ChatWindow → suggestion chips when no messages |
| 10 | **Dynamic inline styles** | HabitCard → `style={{ backgroundColor: habit.color }}` |

---

## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16d: Layout Components](./phase4-part16d-frontend-layout-components.md) |
| ➡️ Next | [Part 16f: Pages](./phase4-part16f-frontend-pages.md) |

---

**End of Phase 4 Part 16e: Feature Components**
