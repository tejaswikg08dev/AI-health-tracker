# 🔄 Phase 4 Part 16g: Frontend — Entry Point, Routing & End-to-End Flows

> **"main.tsx wraps the app in three providers (StrictMode, QueryClient, BrowserRouter). App.tsx defines all routes with nested layouts. Then we trace three complete user journeys — login, daily check-in, and AI chat — from click to database and back."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16f-frontend-pages.md](./phase4-part16f-frontend-pages.md) |
| **Next** | [Phase 5: Testing](./phase5-part01-testing-overview-infrastructure.md) |
| **Files in This Doc** | 2 files (main.tsx, App.tsx) + 3 E2E flow traces |
| **Time to Type** | ~15 minutes (code) + reading time (flows) |
| **Difficulty** | Easy (code) / Conceptual (flows tie everything together) |

---

## 1. `src/main.tsx` — Application Entry Point

### Type This Code:

```typescript
// ============================================================================
// App Entry Point — React root with providers
// ============================================================================

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

// TanStack Query client — global cache configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,                    // Retry failed requests once
      staleTime: 5 * 60 * 1000,   // 5 min default — data considered fresh
      refetchOnWindowFocus: true,  // Refetch when user tabs back
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
```

### Provider Nesting (Outside → Inside)

```
<React.StrictMode>                    ← Development checks (double-renders to find bugs)
  <QueryClientProvider client={...}>  ← TanStack Query cache available everywhere
    <BrowserRouter>                   ← React Router context (useNavigate, NavLink work)
      <App />                         ← Your routes and pages
    </BrowserRouter>
  </QueryClientProvider>
</React.StrictMode>
```

**Why this order matters:**
- `QueryClientProvider` must wrap everything that uses `useQuery`/`useMutation`
- `BrowserRouter` must wrap everything that uses `<Route>`, `<Link>`, `useNavigate`
- `StrictMode` wraps everything — it's a development tool that double-invokes functions to catch side effects. It does NOT run in production builds.

**`document.getElementById("root")!`** — The `!` is a non-null assertion. TypeScript knows `getElementById` can return `null`, but we know `index.html` has `<div id="root">`. The `!` tells TypeScript "trust me, this is not null."

**QueryClient defaults:**
- `retry: 1` — If an API call fails, retry once. Handles transient network errors.
- `staleTime: 5 * 60 * 1000` — 5 minutes. During this window, TanStack Query serves cached data without refetching. Individual hooks override this (analytics uses 30 min).
- `refetchOnWindowFocus: true` — When the user switches tabs and comes back, data is refetched in the background. Keeps the dashboard current.

---

## 2. `src/App.tsx` — Route Definitions

### Type This Code:

```typescript
// ============================================================================
// App — Root component with routing
// ============================================================================

import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";
import PageLayout from "@/components/layout/PageLayout";
import ProtectedRoute from "@/components/layout/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import DashboardPage from "@/pages/DashboardPage";
import HabitsPage from "@/pages/HabitsPage";
import CheckInPage from "@/pages/CheckInPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import ChatPage from "@/pages/ChatPage";
import SettingsPage from "@/pages/SettingsPage";

export default function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/signup"
        element={isAuthenticated ? <Navigate to="/" replace /> : <SignupPage />}
      />

      {/* Protected routes — wrapped in layout with sidebar + navbar */}
      <Route element={<ProtectedRoute />}>
        <Route element={<PageLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/habits" element={<HabitsPage />} />
          <Route path="/check-in" element={<CheckInPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      {/* Catch-all → redirect to dashboard or login */}
      <Route
        path="*"
        element={<Navigate to={isAuthenticated ? "/" : "/login"} replace />}
      />
    </Routes>
  );
}
```

### Route Nesting Diagram

```
Routes
├── /login          → LoginPage (or redirect to / if already logged in)
├── /signup         → SignupPage (or redirect to / if already logged in)
│
├── <ProtectedRoute>                    ← Auth check layer
│   └── <PageLayout>                    ← Navbar + Sidebar + <Outlet/>
│       ├── /            → DashboardPage
│       ├── /habits      → HabitsPage
│       ├── /check-in    → CheckInPage
│       ├── /analytics   → AnalyticsPage
│       ├── /chat        → ChatPage
│       └── /settings    → SettingsPage
│
└── *               → Redirect (to / or /login based on auth)
```

**Two layers of layout routes:**
1. `<ProtectedRoute>` — Checks `isAuthenticated`. If false → redirect to `/login`. If true → render `<Outlet/>` (which is PageLayout).
2. `<PageLayout>` — Renders Navbar + Sidebar + `<Outlet/>` (which is the actual page component).

**Login/Signup redirect:** If the user is already authenticated and visits `/login`, they're redirected to `/`. This prevents the "logged in but seeing the login page" confusion.

**Catch-all `*`:** Any unrecognized URL (like `/nonexistent`) redirects to the dashboard (if authed) or login (if not). No 404 page needed for a personal app.

---

## 3. Flow 1: User Logs In → Sees Dashboard

```
USER: Types email + password, clicks "Sign in"

 1  LoginPage.handleSubmit()
      → e.preventDefault()  — stop page reload
      → setError("")        — clear previous errors

 2  useAuthStore.login(email, password)
      → set({ isLoading: true })
      → authService.login({ email, password })
        → api.post<AuthTokens>("/auth/login", data)
          → Vite proxy → http://localhost:8000/api/v1/auth/login
            → FastAPI AuthRouter.login()
              → AuthService.authenticate()
                → AuthRepository.get_by_email()
                  → SELECT * FROM users WHERE email = 'shreya@test.com'
                → bcrypt.verify(password, hashed)  ✅
              → create_access_token() + create_refresh_token()
            ← { access_token: "eyJ...", refresh_token: "eyJ..." }
          ← 200 OK
        ← tokens
      → localStorage.setItem("access_token", tokens.access_token)
      → localStorage.setItem("refresh_token", tokens.refresh_token)

 3  useAuthStore → authService.getProfile()
      → api.get<User>("/auth/me")
        → Request interceptor attaches: Authorization: Bearer eyJ...
        → FastAPI → decode JWT → AuthRepository.get_by_id()
        ← { id: "uuid", email: "shreya@test.com", full_name: "Shreya" }
      → localStorage.setItem("user", JSON.stringify(user))
      → set({ user, isAuthenticated: true, isLoading: false })

 4  LoginPage
      → navigate("/")  — React Router navigates to DashboardPage
      → App.tsx: isAuthenticated is true → ProtectedRoute passes
      → PageLayout renders: Navbar + Sidebar + DashboardPage

 5  DashboardPage mounts
      → useDashboard() → queryFn → analyticsService.getDashboard()
        → api.get("/analytics/dashboard")
          → FastAPI → AnalyticsService → 5 SQL queries
          ← { today_logged: 4, today_total: 6, ... }
      → useStreaks() → queryFn → analyticsService.getStreaks()
        → api.get("/analytics/streaks")
          → gaps-and-islands SQL
          ← { streaks: [{ habit_name: "Water", current_streak: 30, ... }] }
      → Dashboard renders: 4 summary cards + streaks list

TOTAL TIME: ~500ms (login) + ~200ms (dashboard load)
User sees: Login form → spinner → Dashboard with data
```

---

## 4. Flow 2: User Logs Today's Habits

```
USER: Navigates to /check-in, logs Water = 8 glasses, Sleep = ✅, Mood = 7

 1  CheckInPage mounts
      → useHabits() fetches 6 habits (cached from earlier → instant)
      → useLogsByDate("2026-09-26") fetches today's existing logs
        → api.get("/logs?date=2026-09-26")
        ← [] (no logs yet for today)
      → DailyCheckIn renders: 6 habit rows with empty inputs

 2  User fills in values:
      → Water: types "8" → updateValue("water-id", "numeric", 8)
      → Sleep: clicks "Not yet" → toggles to "✅ Done"
      → Mood: drags slider to 7 → updateValue("mood-id", "scale", 7)
      (Local state updates — no API calls yet)

 3  User clicks "Save All"
      → handleSave() builds BulkLogCreate:
        {
          log_date: "2026-09-26",
          entries: [
            { habit_id: "water-id", value_numeric: 8 },
            { habit_id: "sleep-id", value_boolean: true },
            { habit_id: "mood-id", value_scale: 7 },
            ... (3 more habits)
          ]
        }
      → bulkCreate.mutateAsync(data)
        → logService.bulkCreateLogs(data)
          → api.post("/logs/bulk", data)
            → FastAPI LogRouter.bulk_create()
              → LogService → 6x INSERT INTO habit_logs
              → SQS: streak check messages for each habit
            ← [6 HabitLog objects]

 4  TanStack Query onSuccess:
      → invalidateQueries({ queryKey: LOGS_KEY })
        → useLogsByDate("2026-09-26") refetches → now shows 6 logs
        → Green borders + ✅ icons appear on each habit row
      → invalidateQueries({ queryKey: ANALYTICS_KEY })
        → Dashboard data is now stale
        → Next visit to Dashboard auto-refetches (fresh numbers)

 5  Button shows "✅ Saved!" for 2 seconds, then reverts to "Save All"

 6  (Background) Lambda 4 processes SQS messages:
      → Calculates streaks → Water = 31 days (milestone!)
      → Sends email: "🔥 31-Day Streak on Water Intake!"

TOTAL TIME: ~300ms for the save. User sees green checkmarks instantly.
Analytics cache invalidated — dashboard shows updated numbers on next visit.
```

---

## 5. Flow 3: User Asks AI Coach a Question

```
USER: Navigates to /chat, types "How's my sleep this week?"

 1  ChatPage mounts
      → useChat().loadHistory()
        → aiService.getChatHistory()
          → api.get("/ai/chat/history")
          ← { messages: [...previous messages...] }
        → setMessages(history)

 2  User types "How's my sleep this week?" and presses Enter
      → ChatInput.handleSubmit()
        → setMessage("") — clears input immediately
        → onSend("How's my sleep this week?")

 3  useChat.sendMessage()
      → setIsLoading(true)
      → Optimistic update: add user message to UI immediately
        { role: "user", content: "How's my sleep this week?" }
        → ChatWindow shows the message + "Thinking..." spinner

 4  aiService.chat({ message, use_agent: true })
      → api.post("/ai/chat", { message: "How's my sleep...", use_agent: true })
        → FastAPI AiRouter.chat()
          → AiService.chat() → ReAct Agent loop:
            → Thought: "User wants sleep data for this week"
            → Action: get_weekly_summary tool
              → AnalyticsRepository.get_weekly_summary()
              → SQL: SELECT AVG(value_numeric)... WHERE habit_type = 'Sleep'
            → Observation: "Sleep avg: 7.2h this week, 6.8h last week"
            → Thought: "Improvement. Let me respond."
            → Final Answer: "Your sleep averaged 7.2 hours this week,
               up from 6.8 last week. That's a 6% improvement! 🎉"
          → INSERT INTO ai_chat_messages (user msg + assistant msg)
        ← { response: "Your sleep averaged 7.2 hours..." }

 5  useChat.sendMessage() continues
      → Add assistant message to UI:
        { role: "assistant", content: "Your sleep averaged 7.2 hours..." }
      → setIsLoading(false) — spinner disappears
      → ChatWindow auto-scrolls to bottom (useRef + scrollIntoView)

USER SEES:
  You: How's my sleep this week?
  🤖: Your sleep averaged 7.2 hours this week, up from 6.8 last week.
      That's a 6% improvement! 🎉

TOTAL TIME: ~2-5 seconds (AI processing). User message appears instantly (optimistic).
```

---

## 6. Frontend Module Summary

### What You Built (Parts 16–16g)

| Part | Files | What It Does |
|------|-------|-------------|
| **16** | — | Overview: 50-file structure, tech stack, architecture |
| **16a** | 12 | Config (package.json, Vite, TS, Tailwind) + 7 type files |
| **16b** | 8 | API client (interceptors, token refresh) + 7 services |
| **16c** | 5 | Zustand auth store + 4 TanStack Query hook files |
| **16d** | 6 | Layout (PageLayout, Navbar, Sidebar, ProtectedRoute) + utils |
| **16e** | 9 | Feature components (habits, logs, charts, AI chat) |
| **16f** | 8 | All 8 pages (Login through Settings) |
| **16g** | 2 | Entry point (main.tsx, App.tsx) + 3 E2E flows |

### By the Numbers

| Metric | Value |
|--------|-------|
| Total frontend files | ~50 |
| Pages | 8 (2 public, 6 protected) |
| Reusable components | 14 (5 layout + 9 feature) |
| API service files | 8 (1 client + 7 modules) |
| TanStack Query hooks | 20+ (across 4 hook files) |
| Recharts visualizations | 3 (bar, line, pie) |
| TypeScript interfaces | 30+ (across 7 type files) |
| External dependencies | 14 runtime + 8 dev |

### Frontend Module — All Sub-Parts Complete ✅

| Sub-Part | Status |
|----------|--------|
| 16a | ✅ Setup, Config & Types |
| 16b | ✅ API Client & Services |
| 16c | ✅ Store & Hooks |
| 16d | ✅ Layout Components |
| 16e | ✅ Feature Components |
| 16f | ✅ Pages |
| **16g** | ✅ **Entry, Routing & Flows** |

---

## 7. Interview Questions

### Q1: "Walk me through what happens when a user opens your app."

**A:** The browser loads `index.html` which includes the bundled JavaScript. `main.tsx` runs first — it creates the TanStack Query client, wraps the app in three providers (StrictMode, QueryClient, BrowserRouter), and renders `App.tsx`. App checks `isAuthenticated` from the Zustand store, which reads `localStorage` for a saved token. If a token exists, the user sees the dashboard (with PageLayout wrapper). If not, they see the login page. On the dashboard, `useDashboard()` fires a GET request through the axios instance, which auto-attaches the JWT token via the request interceptor.

### Q2: "How does your app stay in sync across tabs?"

**A:** TanStack Query's `refetchOnWindowFocus: true`. When a user logs habits in Tab A, then switches to Tab B (which shows the dashboard), TanStack Query detects the window focus event and refetches stale queries in the background. The dashboard updates with the latest numbers without the user doing anything. Additionally, the Zustand auth store reads from localStorage, which is shared across tabs — if the user logs out in one tab, the other tab's next API call would fail with 401 and redirect to login.

### Q3: "Why did you use nested routes instead of flat routes?"

**A:** Nested routes eliminate duplication. Without nesting, every protected page would need to individually check authentication and render its own Navbar/Sidebar. With nesting, `ProtectedRoute` checks auth ONCE for all child routes, and `PageLayout` renders the shell ONCE. Adding a new page is one line: `<Route path="/new-page" element={<NewPage />} />`. The layout and auth check are inherited automatically.

---

## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16f: Pages](./phase4-part16f-frontend-pages.md) |
| ➡️ Next | [Phase 5: Testing Overview](./phase5-part01-testing-overview-infrastructure.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**🎉 The Frontend module is COMPLETE.**

*50 files: 8 pages, 14 components, 8 services, 4 hook files, 1 Zustand store, 7 type definitions, 3 Recharts visualizations, and an AI chat interface. All connected to your FastAPI backend via axios with automatic JWT token management. Next: testing, Docker, CI/CD, and deployment.*
