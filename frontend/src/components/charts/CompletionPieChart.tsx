// Completion pie chart — shows completion % per habit

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { HabitCompletionRate } from "@/types/analytics";

interface CompletionPieChartProps {
  data: HabitCompletionRate[];
}

export default function CompletionPieChart({ data }: CompletionPieChartProps) {
  if (!data.length) return <p className="text-gray-500 text-center py-8">No completion data yet.</p>;

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
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={3}
            dataKey="value"
            label={({ name, value }) => `${name}: ${value}%`}
          >
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
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
            <div className="flex-1">
              <p className="text-sm font-medium">{item.icon} {item.name}</p>
              <p className="text-xs text-gray-500">{item.days} — {item.value.toFixed(0)}%</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
