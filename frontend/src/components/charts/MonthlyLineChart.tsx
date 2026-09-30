// Monthly line chart — 30-day trends for all habits

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { HabitTrendData } from "@/types/analytics";

interface MonthlyLineChartProps {
  data: HabitTrendData[];
}

export default function MonthlyLineChart({ data }: MonthlyLineChartProps) {
  if (!data.length) return <p className="text-gray-500 text-center py-8">No trend data available.</p>;

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
