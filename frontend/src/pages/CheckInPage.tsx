// Check-in page — log all habits for today (or a past date)

import { useState } from "react";
import { useHabits } from "@/hooks/useHabits";
import { useLogsByDate, useBulkCreateLogs } from "@/hooks/useLogs";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import DailyCheckIn from "@/components/logs/DailyCheckIn";
import { todayString } from "@/lib/utils";
import { ChevronLeft, ChevronRight, CalendarCheck } from "lucide-react";

export default function CheckInPage() {
  const [selectedDate, setSelectedDate] = useState(todayString());
  const { data: habits, isLoading: habitsLoading } = useHabits();
  const { data: logs, isLoading: logsLoading } = useLogsByDate(selectedDate);
  const bulkCreate = useBulkCreateLogs();

  const isToday = selectedDate === todayString();

  const changeDate = (days: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + days);
    // Don't allow future dates
    if (d <= new Date()) {
      setSelectedDate(d.toISOString().split("T")[0]);
    }
  };

  if (habitsLoading || logsLoading) {
    return <LoadingSpinner className="h-64" text="Loading..." />;
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Date Navigator */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <CalendarCheck className="w-6 h-6 text-brand-500" />
          Daily Check-in
        </h2>
        <div className="flex items-center gap-3">
          <button
            onClick={() => changeDate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Previous day"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="font-medium text-gray-700 min-w-[140px] text-center">
            {isToday ? "Today" : new Date(selectedDate).toLocaleDateString("en-US", {
              weekday: "short", month: "short", day: "numeric",
            })}
          </span>
          <button
            onClick={() => changeDate(1)}
            disabled={isToday}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30"
            aria-label="Next day"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Check-in Form */}
      {habits && habits.length > 0 ? (
        <DailyCheckIn
          habits={habits}
          existingLogs={logs || []}
          date={selectedDate}
          onSave={bulkCreate.mutateAsync}
          isSaving={bulkCreate.isPending}
        />
      ) : (
        <div className="bg-white rounded-xl border p-12 text-center">
          <span className="text-5xl">📋</span>
          <h3 className="text-lg font-semibold mt-4">No habits to log</h3>
          <p className="text-gray-500 mt-2">
            Create some habits first, then come back to check in!
          </p>
        </div>
      )}
    </div>
  );
}
