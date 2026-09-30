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
