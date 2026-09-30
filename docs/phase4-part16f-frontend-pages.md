# 📄 Phase 4 Part 16f: Frontend — Pages

> **"Eight page components — one per route. Login/Signup are public full-screen forms. The other six are protected: Dashboard (4 summary cards + streaks), Habits (CRUD grid), CheckIn (date navigator + bulk log form), Analytics (4-tab charts), Chat (AI coach), Settings (profile + export)."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16e-frontend-feature-components.md](./phase4-part16e-frontend-feature-components.md) |
| **Next** | [phase4-part16g-frontend-entry-routing-flows.md](./phase4-part16g-frontend-entry-routing-flows.md) |
| **Files in This Doc** | 8 page files |
| **Time to Type** | ~55 minutes |
| **Difficulty** | Medium (composing hooks + components, tab navigation, date navigation) |

---

## 1. `src/pages/LoginPage.tsx` — Public

```typescript
// Login page — email + password form

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";
import { LogIn } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Invalid email or password");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <span className="text-5xl">🏥</span>
          <h1 className="text-2xl font-bold text-gray-900 mt-4">Welcome back</h1>
          <p className="text-gray-500 mt-1">Sign in to your Health Tracker</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}
          className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg"
              role="alert">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input id="email" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              required autoComplete="email"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              placeholder="shreya@example.com" />
          </div>

          <div>
            <label htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input id="password" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              required autoComplete="current-password" minLength={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              placeholder="••••••••" />
          </div>

          <button type="submit" disabled={isLoading}
            className="w-full bg-brand-600 text-white py-2.5 rounded-lg font-medium
              hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center justify-center gap-2 transition-colors">
            <LogIn className="w-4 h-4" />
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Don't have an account?{" "}
          <Link to="/signup" className="text-brand-600 font-medium hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
```

### How Login Connects the Layers

```
LoginPage                    → useAuthStore.login(email, password)
  useAuthStore.login()       → authService.login({ email, password })
    authService.login()      → api.post("/auth/login", data)
      api.ts                 → POST http://localhost:8000/api/v1/auth/login
        FastAPI              → AuthRouter → AuthService → verify password → JWT
      api.ts                 ← { access_token, refresh_token }
    authService              ← tokens
  useAuthStore               ← stores tokens in localStorage, fetches profile
    set({ user, isAuthenticated: true })
LoginPage                    ← navigate("/") → DashboardPage
```

**`e.preventDefault()`** — Prevents the browser from submitting the form as a traditional HTTP request (which would reload the page). In an SPA, we handle form submission in JavaScript.

**`useNavigate()`** — React Router's programmatic navigation. After successful login, `navigate("/")` sends the user to the dashboard without a page reload.

---

## 2. `src/pages/SignupPage.tsx` — Public

```typescript
// Signup page — name + email + password + timezone

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";
import { UserPlus } from "lucide-react";

export default function SignupPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone // Auto-detect user's timezone
  );
  const [error, setError] = useState("");
  const { signup, isLoading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await signup(email, password, fullName, timezone);
      navigate("/");
    } catch {
      setError("Signup failed. Email may already be registered.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <span className="text-5xl">🏥</span>
          <h1 className="text-2xl font-bold text-gray-900 mt-4">Create your account</h1>
          <p className="text-gray-500 mt-1">Start tracking your health habits today</p>
        </div>

        <form onSubmit={handleSubmit}
          className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg"
              role="alert">{error}</div>
          )}

          <div>
            <label htmlFor="name"
              className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input id="name" type="text" value={fullName}
              onChange={(e) => setFullName(e.target.value)} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              placeholder="Shreya" />
          </div>

          <div>
            <label htmlFor="email"
              className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input id="email" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)} required autoComplete="email"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              placeholder="shreya@example.com" />
          </div>

          <div>
            <label htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input id="password" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} required minLength={8}
              autoComplete="new-password"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              placeholder="Min 8 characters" />
          </div>

          <div>
            <label htmlFor="timezone"
              className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
            <input id="timezone" type="text" value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none
                text-sm text-gray-600" />
          </div>

          <button type="submit" disabled={isLoading}
            className="w-full bg-brand-600 text-white py-2.5 rounded-lg font-medium
              hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center justify-center gap-2 transition-colors">
            <UserPlus className="w-4 h-4" />
            {isLoading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-600 font-medium hover:underline">
            Sign in</Link>
        </p>
      </div>
    </div>
  );
}
```

**`Intl.DateTimeFormat().resolvedOptions().timeZone`** — Browser API that detects the user's timezone automatically. Returns strings like `"Asia/Kolkata"`, `"America/New_York"`. Pre-fills the timezone field so the user doesn't need to type it.

**Signup flow:** `signup()` in Zustand calls `authService.signup()` → creates account → then auto-calls `login()` → user lands on dashboard. One click, no extra login step.

---

## 3. `src/pages/DashboardPage.tsx` — Protected

```typescript
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
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          🔥 Current Streaks
        </h3>
        {streaksData?.streaks && streaksData.streaks.length > 0 ? (
          <div className="space-y-3">
            {streaksData.streaks.map((streak) => (
              <div key={streak.habit_id}
                className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <span className="text-xl">{streak.habit_icon}</span>
                  <div>
                    <p className="font-medium text-gray-900">{streak.habit_name}</p>
                    <p className="text-xs text-gray-500">
                      Best: {streak.longest_streak} days
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold"
                    style={{ color: streak.habit_color }}>
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
  icon: React.ReactNode; title: string; value: string;
  subtitle: string; color: string;
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
```

**`const { data: dashboard, isLoading } = useDashboard()`** — Destructuring with rename. TanStack Query returns `{ data, isLoading, error }`. We rename `data` to `dashboard` for clarity.

**`dashboard?.today_logged ?? 0`** — Two safety operators: `?.` (optional chaining — don't crash if dashboard is undefined) and `??` (nullish coalescing — use `0` if the value is `null` or `undefined`).

**`SummaryCard` as a local function** — This component is only used on the dashboard. Instead of creating a separate file, we define it in the same file. It's a common React pattern for page-specific components.

**Responsive grid:** `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` — 1 column on mobile, 2 on tablet, 4 on desktop.

---

## 4. `src/pages/HabitsPage.tsx` — Protected

```typescript
// Habits page — list, create, edit, delete habits

import { useState } from "react";
import { useHabits, useCreateHabit, useDeleteHabit } from "@/hooks/useHabits";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import HabitCard from "@/components/habits/HabitCard";
import HabitForm from "@/components/habits/HabitForm";
import { Plus } from "lucide-react";
import type { HabitCreate } from "@/types/habit";

export default function HabitsPage() {
  const { data: habits, isLoading } = useHabits();
  const createHabit = useCreateHabit();
  const deleteHabit = useDeleteHabit();
  const [showForm, setShowForm] = useState(false);

  const handleCreate = async (data: HabitCreate) => {
    await createHabit.mutateAsync(data);
    setShowForm(false);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Archive this habit? You can restore it later.")) {
      await deleteHabit.mutateAsync(id);
    }
  };

  if (isLoading) return <LoadingSpinner className="h-64" text="Loading habits..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">My Habits</h2>
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2
            rounded-lg hover:bg-brand-700 transition-colors">
          <Plus className="w-4 h-4" />
          Add Habit
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h3 className="text-lg font-semibold mb-4">Create New Habit</h3>
          <HabitForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
            isLoading={createHabit.isPending}
          />
        </div>
      )}

      {/* Habits Grid */}
      {habits && habits.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {habits.map((habit) => (
            <HabitCard key={habit.id} habit={habit} onDelete={handleDelete} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border p-12 text-center">
          <span className="text-5xl">🎯</span>
          <h3 className="text-lg font-semibold mt-4">No habits yet</h3>
          <p className="text-gray-500 mt-2">
            Create your first habit to start tracking!
          </p>
        </div>
      )}
    </div>
  );
}
```

**`createHabit.mutateAsync(data)`** — TanStack Query's mutation. `mutateAsync` returns a promise (vs `mutate` which is fire-and-forget). We `await` it so the form closes only AFTER the API succeeds.

**`createHabit.isPending`** — TanStack Query tracks mutation state. While the API call is in flight, `isPending` is `true`. HabitForm uses this to show "Creating..." and disable the button.

**Empty state pattern:** When `habits.length === 0`, show a friendly message with an emoji and instruction instead of a blank page.

---

## 5. `src/pages/CheckInPage.tsx` — Protected

```typescript
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
          <button onClick={() => changeDate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Previous day">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="font-medium text-gray-700 min-w-[140px] text-center">
            {isToday ? "Today" : new Date(selectedDate).toLocaleDateString("en-US", {
              weekday: "short", month: "short", day: "numeric",
            })}
          </span>
          <button onClick={() => changeDate(1)} disabled={isToday}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors
              disabled:opacity-30"
            aria-label="Next day">
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
```

**Date navigation:** The `< Today >` navigator lets users go back to log past dates but blocks future dates (`d <= new Date()`). When `selectedDate` changes, `useLogsByDate(selectedDate)` auto-refetches logs for that date — TanStack Query creates a new cache entry per date.

**`onSave={bulkCreate.mutateAsync}`** — Passes the mutation function directly as a prop. DailyCheckIn calls it with `BulkLogCreate` data. On success, both `LOGS_KEY` and `ANALYTICS_KEY` caches are invalidated (defined in useLogs.ts).

---

## 6. `src/pages/AnalyticsPage.tsx` — Protected

```typescript
// Analytics page — streaks, weekly comparison, monthly trends, correlations

import { useState } from "react";
import {
  useStreaks, useWeeklySummary, useMonthlyTrend,
  useCompletionRate, useCorrelations,
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
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}>
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
                  <div key={h.habit_id}
                    className="flex items-center justify-between py-2
                      border-b last:border-0">
                    <span className="font-medium">{h.habit_name}</span>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-gray-500">
                        {h.last_week_avg?.toFixed(1) ?? "—"}
                      </span>
                      <span>→</span>
                      <span className="font-semibold">
                        {h.this_week_avg?.toFixed(1) ?? "—"}
                      </span>
                      {h.change_pct != null && (
                        <span className={`flex items-center gap-0.5 ${
                          h.change_pct > 0 ? "text-green-600"
                            : h.change_pct < 0 ? "text-red-600"
                            : "text-gray-400"
                        }`}>
                          {h.change_pct > 0 ? <ArrowUpRight className="w-3 h-3" />
                            : h.change_pct < 0 ? <ArrowDownRight className="w-3 h-3" />
                            : <Minus className="w-3 h-3" />}
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
              <h3 className="text-lg font-semibold mb-4">
                Completion Rates (Last 30 Days)
              </h3>
              {completion?.habits && <CompletionPieChart data={completion.habits} />}
            </div>
          )
        )}

        {activeTab === "correlations" && (
          corrLoading ? <LoadingSpinner className="h-64" /> : (
            <div>
              <h3 className="text-lg font-semibold mb-4">Habit Correlations</h3>
              {correlations?.correlations &&
                correlations.correlations.length > 0 ? (
                <div className="space-y-4">
                  {correlations.correlations.map((c, i) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">
                          {c.habit_a_name} ↔ {c.habit_b_name}
                        </span>
                        <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                          c.strength === "strong"
                            ? "bg-green-100 text-green-700"
                            : c.strength === "moderate"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-gray-100 text-gray-500"
                        }`}>
                          {c.correlation.toFixed(2)} ({c.strength})
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">{c.insight}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {c.data_points} data points
                      </p>
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
```

**Tab pattern:** `type Tab = "weekly" | "monthly" | "completion" | "correlations"` — TypeScript literal union ensures `activeTab` can only be one of these four values. The tab buttons set state, and conditional rendering shows the matching chart.

**All 4 hooks fire on mount** — TanStack Query caches them all. Switching tabs shows cached data instantly (no loading spinner after the first load). The `staleTime` in useAnalytics.ts controls how long before a background refetch.

---

## 7. `src/pages/ChatPage.tsx` — Protected

```typescript
// AI Chat page — conversation with the health coach agent

import { useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import ChatWindow from "@/components/ai/ChatWindow";
import ChatInput from "@/components/ai/ChatInput";
import { MessageSquare, Sparkles } from "lucide-react";

export default function ChatPage() {
  const { messages, isLoading, sendMessage, loadHistory } = useChat();

  // Load chat history on mount
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  return (
    <div className="flex flex-col h-[calc(100vh-130px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-brand-500" />
          AI Health Coach
        </h2>
        <div className="flex items-center gap-1 text-xs text-gray-400
          bg-gray-100 px-2 py-1 rounded-full">
          <Sparkles className="w-3 h-3" />
          Agent mode — can access your data
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 bg-white rounded-xl border overflow-hidden flex flex-col">
        <ChatWindow messages={messages} isLoading={isLoading} />
        <ChatInput onSend={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}
```

**`h-[calc(100vh-130px)]`** — Tailwind arbitrary value. The chat needs to fill the remaining viewport height (minus 130px for navbar + header). This is CSS `height: calc(100vh - 130px)`.

**Simplest page:** ChatPage is just composition — it connects the `useChat` hook to the `ChatWindow` and `ChatInput` components. All the logic lives in the hook and components.

---

## 8. `src/pages/SettingsPage.tsx` — Protected

```typescript
// Settings page — profile, notifications, data export

import { useState } from "react";
import { useAuthStore } from "@/store/auth-store";
import { authService } from "@/services/auth.service";
import { notificationService } from "@/services/notification.service";
import { exportService } from "@/services/export.service";
import { todayString } from "@/lib/utils";
import { Settings, Bell, Download, User } from "lucide-react";

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [timezone, setTimezone] = useState(user?.timezone || "UTC");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const handleProfileSave = async () => {
    setSaving(true);
    try {
      const updated = await authService.updateProfile({
        full_name: fullName, timezone
      });
      setUser(updated);
      setMessage("Profile updated!");
    } catch {
      setMessage("Failed to update profile.");
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(""), 3000);
    }
  };

  const handleExport = async () => {
    try {
      setMessage("Generating export...");
      // Export last 90 days
      const d = new Date();
      d.setDate(d.getDate() - 90);
      const startDate = d.toISOString().split("T")[0];
      const blob = await exportService.exportCsv(startDate, todayString());
      exportService.downloadBlob(blob,
        `health-tracker-export-${todayString()}.csv`);
      setMessage("Export downloaded!");
    } catch {
      setMessage("Export failed.");
    }
    setTimeout(() => setMessage(""), 3000);
  };

  const handleTestEmail = async () => {
    try {
      const res = await notificationService.sendTestEmail();
      setMessage(res.message);
    } catch {
      setMessage("Failed to send test email.");
    }
    setTimeout(() => setMessage(""), 3000);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <Settings className="w-6 h-6 text-brand-500" />
        Settings
      </h2>

      {message && (
        <div className="bg-brand-50 text-brand-700 text-sm px-4 py-3 rounded-lg">
          {message}
        </div>
      )}

      {/* Profile Section */}
      <section className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <User className="w-5 h-5" /> Profile
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email</label>
            <input type="email" value={user?.email || ""} disabled
              className="w-full px-3 py-2 border border-gray-200 rounded-lg
                bg-gray-50 text-gray-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name</label>
            <input type="text" value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent
                outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Timezone</label>
            <input type="text" value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                focus:ring-2 focus:ring-brand-500 focus:border-transparent
                outline-none" />
          </div>
          <button onClick={handleProfileSave} disabled={saving}
            className="bg-brand-600 text-white px-4 py-2 rounded-lg
              hover:bg-brand-700 disabled:opacity-50 transition-colors">
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5" /> Notifications
        </h3>
        <p className="text-sm text-gray-500 mb-4">Email notification settings</p>
        <button onClick={handleTestEmail}
          className="text-sm text-brand-600 hover:underline">
          Send test email →
        </button>
      </section>

      {/* Export Section */}
      <section className="bg-white rounded-xl border p-6">
        <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Download className="w-5 h-5" /> Export Data
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          Download your habit data as a CSV file.
        </p>
        <button onClick={handleExport}
          className="bg-green-600 text-white px-4 py-2 rounded-lg
            hover:bg-green-700 transition-colors flex items-center gap-2">
          <Download className="w-4 h-4" /> Export Last 90 Days (CSV)
        </button>
      </section>
    </div>
  );
}
```

**`setUser(updated)`** — After updating the profile via API, we update the Zustand store with the new user object. This also updates localStorage (inside `setUser`), so the Navbar shows the new name immediately.

**`setTimeout(() => setMessage(""), 3000)`** — Auto-dismissing feedback. The success/error message disappears after 3 seconds. A production app would use a toast library (like react-hot-toast), but this pattern works for a personal app.

**Settings calls services directly** — Unlike other pages that use TanStack Query hooks, Settings calls services directly with `useState` for loading. Profile updates, test emails, and exports are one-off actions, not cached data — TanStack Query wouldn't add value here.

---

## 9. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **`e.preventDefault()`** | LoginPage — stop form from reloading the page |
| 2 | **`useNavigate()`** | Login/Signup — programmatic navigation after auth |
| 3 | **Timezone auto-detection** | SignupPage — `Intl.DateTimeFormat().resolvedOptions()` |
| 4 | **Destructuring with rename** | DashboardPage — `{ data: dashboard }` |
| 5 | **`??` nullish coalescing** | DashboardPage — fallback for null API values |
| 6 | **Local component** | DashboardPage — `SummaryCard` defined in same file |
| 7 | **`mutateAsync` vs `mutate`** | HabitsPage — await the promise to close form |
| 8 | **Date navigation** | CheckInPage — `< Today >` with future blocked |
| 9 | **Tab state pattern** | AnalyticsPage — `type Tab` + conditional rendering |
| 10 | **`calc()` in Tailwind** | ChatPage — `h-[calc(100vh-130px)]` |
| 11 | **Auto-dismiss messages** | SettingsPage — `setTimeout` clears feedback |
| 12 | **Direct service calls** | SettingsPage — no TanStack for one-off actions |

---

## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16e: Feature Components](./phase4-part16e-frontend-feature-components.md) |
| ➡️ Next | [Part 16g: Entry, Routing & Flows](./phase4-part16g-frontend-entry-routing-flows.md) |

---

**End of Phase 4 Part 16f: Pages**
