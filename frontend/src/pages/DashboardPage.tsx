// Dashboard — main landing page with summary cards, streaks, and weekly chart

import { useDashboard, useStreaks } from "@/hooks/useAnalytics";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import { Flame, Target, TrendingUp, CheckCircle2 } from "lucide-react";

export default function DashboardPage() {
  const { data: dashboard, isLoading } = useDashboard();
  const { data: streaksData } = useStreaks();

  if (isLoading) return <LoadingSpinner className="h-64" text="Loading dashboard..." />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          icon={<CheckCircle2 className="w-6 h-6 text-green-500" />}
          title="Today's Progress"
          value={`${dashboard?.today_logged ?? 0} / ${dashboard?.today_total ?? 0}`}
          subtitle={`${dashboard?.today_completion_pct ?? 0}% complete`}
          color="green"
        />
        <SummaryCard
          icon={<Target className="w-6 h-6 text-blue-500" />}
          title="Active Habits"
          value={String(dashboard?.total_active_habits ?? 0)}
          subtitle="habits being tracked"
          color="blue"
        />
        <SummaryCard
          icon={<Flame className="w-6 h-6 text-orange-500" />}
          title="Best Streak"
          value={dashboard?.current_best_streak
            ? `${dashboard.current_best_streak.current_streak} days`
            : "No streaks yet"}
          subtitle={dashboard?.current_best_streak?.habit_name ?? "Start logging!"}
          color="orange"
        />
        <SummaryCard
          icon={<TrendingUp className="w-6 h-6 text-purple-500" />}
          title="Weekly Completion"
          value={`${dashboard?.week_completion_pct ?? 0}%`}
          subtitle="average this week"
          color="purple"
        />
      </div>

      {/* Streaks List */}
      <div className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔥 Current Streaks</h3>
        {streaksData?.streaks && streaksData.streaks.length > 0 ? (
          <div className="space-y-3">
            {streaksData.streaks.map((streak) => (
              <div key={streak.habit_id} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{streak.habit_icon}</span>
                  <div>
                    <p className="font-medium text-gray-900">{streak.habit_name}</p>
                    <p className="text-xs text-gray-500">Best: {streak.longest_streak} days</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold" style={{ color: streak.habit_color }}>
                    {streak.current_streak}
                  </span>
                  <span className="text-sm text-gray-500">days</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">
            Start logging habits to build streaks! 🚀
          </p>
        )}
      </div>
    </div>
  );
}

// Summary card component (local to this page)
function SummaryCard({ icon, title, value, subtitle, color }: {
  icon: React.ReactNode; title: string; value: string; subtitle: string; color: string;
}) {
  return (
    <div className="bg-white rounded-xl border p-5">
      <div className="flex items-center gap-3 mb-3">
        {icon}
        <span className="text-sm font-medium text-gray-500">{title}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
    </div>
  );
}
