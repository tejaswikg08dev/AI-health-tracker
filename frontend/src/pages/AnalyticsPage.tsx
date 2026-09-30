// Analytics page — streaks, weekly comparison, monthly trends, correlations

import { useState } from "react";
import {
  useStreaks,
  useWeeklySummary,
  useMonthlyTrend,
  useCompletionRate,
  useCorrelations,
} from "@/hooks/useAnalytics";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import WeeklyBarChart from "@/components/charts/WeeklyBarChart";
import MonthlyLineChart from "@/components/charts/MonthlyLineChart";
import CompletionPieChart from "@/components/charts/CompletionPieChart";
import { TrendingUp, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

type Tab = "weekly" | "monthly" | "completion" | "correlations";

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("weekly");
  const { data: weekly, isLoading: weeklyLoading } = useWeeklySummary();
  const { data: monthly, isLoading: monthlyLoading } = useMonthlyTrend();
  const { data: completion, isLoading: completionLoading } = useCompletionRate();
  const { data: correlations, isLoading: corrLoading } = useCorrelations();

  const tabs: { key: Tab; label: string }[] = [
    { key: "weekly", label: "Weekly" },
    { key: "monthly", label: "Monthly Trend" },
    { key: "completion", label: "Completion" },
    { key: "correlations", label: "Correlations" },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <TrendingUp className="w-6 h-6 text-brand-500" />
        Analytics
      </h2>

      {/* Tab navigation */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-xl border p-6">
        {activeTab === "weekly" && (
          weeklyLoading ? <LoadingSpinner className="h-64" /> : (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold">This Week vs Last Week</h3>
              {weekly?.habits && <WeeklyBarChart data={weekly.habits} />}
              <div className="space-y-2 mt-4">
                {weekly?.habits.map((h) => (
                  <div key={h.habit_id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <span className="font-medium">{h.habit_name}</span>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-gray-500">{h.last_week_avg?.toFixed(1) ?? "—"}</span>
                      <span>→</span>
                      <span className="font-semibold">{h.this_week_avg?.toFixed(1) ?? "—"}</span>
                      {h.change_pct != null && (
                        <span className={`flex items-center gap-0.5 ${h.change_pct > 0 ? "text-green-600" : h.change_pct < 0 ? "text-red-600" : "text-gray-400"}`}>
                          {h.change_pct > 0 ? <ArrowUpRight className="w-3 h-3" /> : h.change_pct < 0 ? <ArrowDownRight className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                          {Math.abs(h.change_pct).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        )}

        {activeTab === "monthly" && (
          monthlyLoading ? <LoadingSpinner className="h-64" /> : (
            <div>
              <h3 className="text-lg font-semibold mb-4">30-Day Trends</h3>
              {monthly?.habits && <MonthlyLineChart data={monthly.habits} />}
            </div>
          )
        )}

        {activeTab === "completion" && (
          completionLoading ? <LoadingSpinner className="h-64" /> : (
            <div>
              <h3 className="text-lg font-semibold mb-4">Completion Rates (Last 30 Days)</h3>
              {completion?.habits && <CompletionPieChart data={completion.habits} />}
            </div>
          )
        )}

        {activeTab === "correlations" && (
          corrLoading ? <LoadingSpinner className="h-64" /> : (
            <div>
              <h3 className="text-lg font-semibold mb-4">Habit Correlations</h3>
              {correlations?.correlations && correlations.correlations.length > 0 ? (
                <div className="space-y-4">
                  {correlations.correlations.map((c, i) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{c.habit_a_name} ↔ {c.habit_b_name}</span>
                        <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                          c.strength === "strong" ? "bg-green-100 text-green-700" :
                          c.strength === "moderate" ? "bg-yellow-100 text-yellow-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {c.correlation.toFixed(2)} ({c.strength})
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">{c.insight}</p>
                      <p className="text-xs text-gray-400 mt-1">{c.data_points} data points</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  Log more habits to discover correlations between them.
                </p>
              )}
            </div>
          )
        )}
      </div>
    </div>
  );
}
