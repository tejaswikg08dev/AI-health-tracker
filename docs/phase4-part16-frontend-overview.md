# 🖥️ Phase 4 Part 16: Frontend Module — Overview

> **"A complete React 18 + TypeScript single-page application with 8 pages, 3 Recharts visualizations, Zustand auth state, TanStack Query data caching, and a real-time AI chat interface — all talking to the FastAPI backend you already built."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 4 — Full-Stack Features |
| **Module** | Frontend (React + TypeScript) |
| **Previous** | [Part 15d: Lambda Flows](./phase4-part15d-lambda-connections-and-flows.md) |
| **Next** | [Part 16a: Setup, Config & Types](./phase4-part16a-frontend-setup-types.md) |
| **Source Files** | ~50 files in `frontend/src/` |
| **Tech Stack** | React 18, TypeScript, Vite, TanStack Query v5, Zustand v4, Recharts, Tailwind CSS |

---

## 1. What Is This Module?

Everything you've built so far (Parts 01–15) is the **backend** — it runs on a server, accepts HTTP requests, returns JSON. Users can't see or interact with JSON directly. They need a **frontend** — a visual application that runs in the browser, shows buttons and forms and charts, and calls your backend API behind the scenes.

This frontend is a **Single-Page Application (SPA)**:
- The browser loads ONE HTML file and ONE JavaScript bundle
- Navigation between pages happens WITHOUT full page reloads
- React Router swaps components in and out — the URL changes, but the browser doesn't reload
- All data comes from your FastAPI API via HTTP calls (axios)

### What the User Sees

```
┌──────────────────────────────────────────────────────────────┐
│  🏥 Health Tracker              [Shreya]  [Logout]           │  ← Navbar
├──────────┬───────────────────────────────────────────────────┤
│          │                                                   │
│ Dashboard│   Dashboard                                       │
│ Habits   │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│ Check In │   │ Today   │ │ Active  │ │ Best    │ │ Week  │ │
│ Analytics│   │ 4/6     │ │ 6 habits│ │ 30 days │ │ 78%   │ │
│ AI Coach │   └─────────┘ └─────────┘ └─────────┘ └───────┘ │
│ Settings │                                                   │
│          │   🔥 Current Streaks                              │
│          │   💧 Water: 30 days  😴 Sleep: 14 days           │
│          │                                                   │
├──────────┴───────────────────────────────────────────────────┤
│  Sidebar        Main Content Area (changes per route)        │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Technology | Version | Purpose | Why This One |
|-----------|---------|---------|-------------|
| **React** | 18.3 | UI library (components) | Industry standard, huge ecosystem |
| **TypeScript** | 5.5 | Type safety | Catches bugs before runtime |
| **Vite** | 5.4 | Build tool + dev server | 10x faster than Webpack |
| **TanStack Query** | 5.56 | Server state (API data caching) | Auto-cache, auto-refetch, loading states |
| **Zustand** | 4.5 | Client state (auth, user) | 1KB, zero boilerplate (vs Redux 10KB+) |
| **Recharts** | 2.12 | Charts (bar, line, pie) | Built on D3, React-native integration |
| **Tailwind CSS** | 3.4 | Styling (utility classes) | No CSS files, responsive by default |
| **Axios** | 1.7 | HTTP client | Interceptors for JWT token injection |
| **React Router** | 6.26 | Client-side routing | Nested layouts, protected routes |
| **Lucide React** | 0.441 | Icons | 1000+ icons, tree-shakable |
| **React Hook Form** | 7.53 | Form handling | Minimal re-renders, validation |
| **Zod** | 3.23 | Schema validation | Type-safe validation for forms |
| **date-fns** | 3.6 | Date utilities | Modular (import only what you need) |

### Two Kinds of State

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND STATE                     │
├───────────────────────┬─────────────────────────────┤
│    SERVER STATE        │     CLIENT STATE             │
│  (data from API)       │  (UI + auth)                 │
│                        │                              │
│  • Habits list         │  • Is user logged in?        │
│  • Today's logs        │  • Current user object       │
│  • Dashboard data      │  • JWT tokens                │
│  • Chat messages       │  • Selected date             │
│  • Analytics           │  • Active tab                │
│                        │                              │
│  Managed by:           │  Managed by:                 │
│  TanStack Query        │  Zustand + useState          │
│  (auto-cache + refetch)│  (persisted to localStorage) │
└───────────────────────┴─────────────────────────────┘
```

**Why two state managers?**
- **TanStack Query** handles data from the server — caching, refetching, loading/error states. Without it, every component needs 10 lines of `useState` + `useEffect` boilerplate.
- **Zustand** handles auth state that needs to persist across page refreshes (localStorage) and be accessible outside React (axios interceptors). Redux would work but requires 10x more code for the same result.

---

## 3. File Structure (50 Files)

```
frontend/
├── package.json                    # Dependencies + scripts
├── vite.config.ts                  # Dev server (port 3000, API proxy)
├── tsconfig.json                   # TypeScript strict mode + @ alias
├── tailwind.config.js              # Brand colors, fonts
├── postcss.config.js               # PostCSS + Tailwind pipeline
├── index.html                      # Single HTML entry point
│
└── src/
    ├── main.tsx                    # React root + providers (Query, Router)
    ├── App.tsx                     # Route definitions (8 routes)
    ├── index.css                   # Tailwind directives + scrollbar
    ├── vite-env.d.ts               # Vite type declarations
    │
    ├── types/                      # TypeScript interfaces (mirror backend schemas)
    │   ├── common.ts               # ApiError, PaginatedResponse<T>
    │   ├── user.ts                 # User, LoginRequest, AuthTokens
    │   ├── habit.ts                # Habit, HabitCreate, HABIT_COLORS/ICONS
    │   ├── log.ts                  # HabitLog, LogCreate, BulkLogCreate
    │   ├── analytics.ts            # DashboardData, StreakInfo, TrendDataPoint...
    │   ├── ai.ts                   # ChatMessage, DocumentInfo, InsightData
    │   └── notification.ts         # NotificationSettings
    │
    ├── services/                   # API call functions (axios wrappers)
    │   ├── api.ts                  # Axios instance + JWT interceptors + token refresh
    │   ├── auth.service.ts         # login, signup, logout, getProfile
    │   ├── habit.service.ts        # CRUD: getHabits, createHabit, deleteHabit...
    │   ├── log.service.ts          # createLog, bulkCreateLogs, getLogsByDate...
    │   ├── analytics.service.ts    # getDashboard, getStreaks, getMonthlyTrend...
    │   ├── ai.service.ts           # chat, streamChat, uploadDocument, getInsights
    │   ├── notification.service.ts # getSettings, updateSettings, sendTestEmail
    │   └── export.service.ts       # exportCsv (blob), exportCsvToS3, downloadBlob
    │
    ├── store/                      # Global state (Zustand)
    │   └── auth-store.ts           # user, isAuthenticated, login(), logout()
    │
    ├── hooks/                      # TanStack Query hooks (server state)
    │   ├── useHabits.ts            # useHabits, useCreateHabit, useDeleteHabit...
    │   ├── useLogs.ts              # useLogsByDate, useBulkCreateLogs...
    │   ├── useAnalytics.ts         # useDashboard, useStreaks, useMonthlyTrend...
    │   └── useChat.ts              # Custom hook: messages state + sendMessage
    │
    ├── lib/                        # Utility functions
    │   └── utils.ts                # cn() (Tailwind merge), formatDate, todayString
    │
    ├── components/                 # Reusable UI components
    │   ├── layout/
    │   │   ├── PageLayout.tsx       # Navbar + Sidebar + <Outlet/>
    │   │   ├── Navbar.tsx           # Top bar: logo, user name, logout
    │   │   ├── Sidebar.tsx          # Left nav: 6 links with icons
    │   │   ├── ProtectedRoute.tsx   # Auth guard: redirect to /login if not authed
    │   │   └── LoadingSpinner.tsx   # Reusable spinner with sizes
    │   ├── habits/
    │   │   ├── HabitCard.tsx        # Single habit display card
    │   │   └── HabitForm.tsx        # Create habit form (name, type, color, icon)
    │   ├── logs/
    │   │   └── DailyCheckIn.tsx     # Bulk log form (numeric/boolean/scale inputs)
    │   ├── charts/
    │   │   ├── WeeklyBarChart.tsx    # This week vs last week (Recharts BarChart)
    │   │   ├── MonthlyLineChart.tsx  # 30-day trend lines (Recharts LineChart)
    │   │   └── CompletionPieChart.tsx# Completion % per habit (Recharts PieChart)
    │   └── ai/
    │       ├── ChatWindow.tsx       # Scrollable message list + auto-scroll
    │       ├── ChatMessage.tsx      # Single message bubble (user/assistant)
    │       └── ChatInput.tsx        # Text input + Send button
    │
    └── pages/                      # Full page components (one per route)
        ├── LoginPage.tsx            # Email + password form
        ├── SignupPage.tsx           # Name + email + password + timezone
        ├── DashboardPage.tsx        # 4 summary cards + streaks list
        ├── HabitsPage.tsx           # Habit list + create form toggle
        ├── CheckInPage.tsx          # Date navigator + daily check-in form
        ├── AnalyticsPage.tsx        # 4 tabs: weekly, monthly, completion, correlations
        ├── ChatPage.tsx             # AI coach chat interface
        └── SettingsPage.tsx         # Profile + notifications + export
```

### Build Order (Type These Files in This Sequence)

| Step | Files | Why This Order |
|------|-------|---------------|
| 1 | Config files (package.json, vite, tsconfig, tailwind) | Foundation: dependencies, build tool, types |
| 2 | types/*.ts (7 files) | TypeScript interfaces before any code that uses them |
| 3 | lib/utils.ts | Utility functions used everywhere |
| 4 | services/api.ts | Axios instance that all services import |
| 5 | services/*.service.ts (7 files) | API functions that hooks call |
| 6 | store/auth-store.ts | Auth state that services and components need |
| 7 | hooks/*.ts (4 files) | TanStack Query hooks that pages use |
| 8 | components/layout/*.tsx (5 files) | Layout shell before page content |
| 9 | components/habits/*.tsx, logs/*.tsx, charts/*.tsx, ai/*.tsx (9 files) | Reusable components before pages |
| 10 | pages/*.tsx (8 files) | Pages that compose everything together |
| 11 | main.tsx, App.tsx, index.css | Entry point: providers + routing + styles |

---

## 4. Route Map (8 Routes)

```
URL              Page Component     Auth Required?   Layout?
─────────────    ─────────────────  ──────────────   ───────
/login           LoginPage          ❌ (public)       No (full screen)
/signup          SignupPage         ❌ (public)       No (full screen)
/                DashboardPage      ✅ (protected)    Yes (Navbar + Sidebar)
/habits          HabitsPage         ✅ (protected)    Yes
/check-in        CheckInPage        ✅ (protected)    Yes
/analytics       AnalyticsPage      ✅ (protected)    Yes
/chat            ChatPage           ✅ (protected)    Yes
/settings        SettingsPage       ✅ (protected)    Yes
*                → Redirect         —                 —
```

### How Protected Routes Work

```
App.tsx Routes:
  /login → LoginPage (if already logged in → redirect to /)
  /signup → SignupPage (if already logged in → redirect to /)

  <ProtectedRoute>        ← checks isAuthenticated from Zustand
    <PageLayout>          ← Navbar + Sidebar + <Outlet/>
      / → DashboardPage
      /habits → HabitsPage
      /check-in → CheckInPage
      ...
    </PageLayout>
  </ProtectedRoute>

  * → redirect to / (if authed) or /login (if not)
```

---

## 5. Architecture: Frontend ↔ Backend

```
┌─────────────────────── BROWSER ──────────────────────────┐
│                                                           │
│  Page (DashboardPage)                                     │
│    │ calls                                                │
│    ▼                                                      │
│  Hook (useDashboard)                                      │
│    │ uses TanStack Query                                  │
│    ▼                                                      │
│  Service (analyticsService.getDashboard)                  │
│    │ calls                                                │
│    ▼                                                      │
│  API Client (api.ts — axios instance)                     │
│    │ attaches JWT token via interceptor                   │
│    │ sends GET /api/v1/analytics/dashboard                │
│    │                                                      │
└────┼──────────────────────────────────────────────────────┘
     │  HTTP (JSON)
     ▼
┌─────────────────────── SERVER ───────────────────────────┐
│  FastAPI Router → Service → Repository → PostgreSQL       │
│  Returns JSON: { today_logged: 4, today_total: 6, ... }  │
└──────────────────────────────────────────────────────────┘
```

**The 5-layer call chain:**
1. **Page** renders UI and calls a hook
2. **Hook** (TanStack Query) manages cache + loading state
3. **Service** makes the actual API call
4. **API Client** (axios) attaches JWT + handles 401 refresh
5. **Backend** processes and returns JSON

---

## 6. Sub-Part Roadmap (7 Documents)

| Doc | Title | Files Covered | Lines |
|-----|-------|--------------|-------|
| **16a** | Setup, Config & Types | package.json, vite.config.ts, tsconfig.json, tailwind.config.js, index.css, 7 type files | ~1200 |
| **16b** | API Client & Services | api.ts (interceptors + token refresh), 7 service files | ~1200 |
| **16c** | Zustand Store & TanStack Hooks | auth-store.ts, useHabits.ts, useLogs.ts, useAnalytics.ts, useChat.ts | ~1000 |
| **16d** | Layout Components | PageLayout, Navbar, Sidebar, ProtectedRoute, LoadingSpinner, utils.ts | ~800 |
| **16e** | Feature Components | HabitCard, HabitForm, DailyCheckIn, 3 chart components, 3 AI chat components | ~1200 |
| **16f** | Pages | All 8 page files: Login, Signup, Dashboard, Habits, CheckIn, Analytics, Chat, Settings | ~1400 |
| **16g** | Entry Point, Routing & Flows | main.tsx, App.tsx, E2E flows (login, check-in, chat), full architecture | ~800 |

---

## 7. Key Concepts You'll Learn

| # | Concept | Where |
|---|---------|-------|
| 1 | **SPA (Single-Page Application)** | Overview — one HTML, React swaps pages |
| 2 | **TypeScript interfaces** | types/ — mirrors backend Pydantic schemas |
| 3 | **Axios interceptors** | api.ts — auto-attach JWT, auto-refresh tokens |
| 4 | **TanStack Query (useQuery/useMutation)** | hooks/ — caching, loading, refetch |
| 5 | **Zustand store** | store/ — global auth state, 1KB vs Redux 10KB |
| 6 | **React Router v6 nested routes** | App.tsx — layout wrapping, Outlet |
| 7 | **Protected routes (auth guard)** | ProtectedRoute.tsx — redirect if not authed |
| 8 | **Tailwind CSS utility classes** | Every component — no CSS files |
| 9 | **Recharts (Bar, Line, Pie)** | charts/ — D3-based, responsive containers |
| 10 | **Component composition** | Pages import hooks + components |
| 11 | **Optimistic UI** | useChat — show user message before API responds |
| 12 | **Cache invalidation** | useLogs — invalidate analytics when logs change |

---

## 8. Design Decisions

### Decision 1: TanStack Query for Server State

```
┌─────────────────────────────────────────────────────────────┐
│ CHOSEN: TanStack Query v5 for all API data                  │
│                                                             │
│ WHY: Auto-caching (5 min staleTime), auto-refetch on focus, │
│ loading/error states built-in. 1 line replaces 10 lines of  │
│ useState + useEffect boilerplate.                           │
│                                                             │
│ ALTERNATIVES:                                               │
│ • SWR (similar, by Vercel) — smaller but less features      │
│ • useEffect + useState — works but massive boilerplate      │
│ • Redux RTK Query — heavier, tightly coupled to Redux       │
│                                                             │
│ TRADE-OFFS:                                                 │
│ + Automatic retry on failure                                │
│ + Queries deduplicated (2 components → 1 fetch)             │
│ + DevTools for debugging cache                              │
│ − Learning curve (queryKey, invalidateQueries)              │
│                                                             │
│ AT SCALE: TanStack Query at 100+ endpoints is standard.     │
│ Large apps add custom queryKey factories.                    │
│                                                             │
│ INTERVIEW TIP: "We separated server state (TanStack Query)  │
│ from client state (Zustand) because they have fundamentally │
│ different caching and lifecycle needs."                      │
└─────────────────────────────────────────────────────────────┘
```

### Decision 2: Zustand over Redux

```
┌─────────────────────────────────────────────────────────────┐
│ CHOSEN: Zustand v4 for auth/client state                    │
│                                                             │
│ WHY: 1KB bundle, zero boilerplate. Can be called outside    │
│ React (needed for axios interceptors). No Provider wrapper. │
│                                                             │
│ ALTERNATIVES:                                               │
│ • Redux Toolkit — industry standard for large apps, 10KB+   │
│ • React Context — built-in but causes unnecessary re-renders│
│ • Jotai/Recoil — atomic state, good but less popular        │
│                                                             │
│ TRADE-OFFS:                                                 │
│ + Minimal code: create<State>((set) => ({ ... }))           │
│ + Works in interceptors (no useContext limitation)           │
│ + Selector-based subscriptions (no wasted re-renders)       │
│ − Less ecosystem than Redux (fewer middleware)              │
│ − No built-in dev tools (but Zustand devtools middleware    │
│   exists)                                                   │
│                                                             │
│ AT SCALE: Zustand works up to ~50 state fields. Beyond      │
│ that, Redux Toolkit with slices is more maintainable.       │
│                                                             │
│ INTERVIEW TIP: "We chose Zustand because auth state is      │
│ small (~5 fields) and needs to be accessible from axios     │
│ interceptors which run outside React's component tree."      │
└─────────────────────────────────────────────────────────────┘
```

### Decision 3: Vite over Webpack

```
┌─────────────────────────────────────────────────────────────┐
│ CHOSEN: Vite 5 as build tool                                │
│                                                             │
│ WHY: Dev server starts in ~300ms (Webpack: 5-30 seconds).   │
│ Hot module replacement (HMR) is instant. Native ES modules. │
│                                                             │
│ ALTERNATIVES:                                               │
│ • Webpack — battle-tested but slow, complex configuration   │
│ • Create React App (CRA) — deprecated, based on Webpack     │
│ • Turbopack — Vercel's new bundler, not yet stable          │
│                                                             │
│ TRADE-OFFS:                                                 │
│ + Zero config for React + TypeScript                        │
│ + Built-in proxy for API during development                 │
│ + path aliases with one line of config                      │
│ − Smaller plugin ecosystem than Webpack                     │
│                                                             │
│ REAL-WORLD: Vite is now the default for new React projects. │
│ Even Vue and Svelte use Vite as their default bundler.      │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Interview Questions

### Q1: "Why separate services from hooks?"

**A:** Services are pure functions that call APIs — they have no React dependencies and can be tested independently or reused outside React (e.g., in a CLI tool). Hooks add React-specific concerns: caching, loading states, cache invalidation. This separation follows the **Single Responsibility Principle** — services handle HTTP, hooks handle state lifecycle.

### Q2: "How does your frontend handle JWT expiration?"

**A:** The axios response interceptor catches 401 errors. It checks if a refresh token exists, calls `POST /auth/refresh`, stores the new tokens, then **retries the original request** with the new token. If multiple requests fail simultaneously, they're queued — only one refresh call is made, and all queued requests are retried with the new token. If refresh fails, the user is redirected to `/login`.

### Q3: "Why not use React Context for auth?"

**A:** Three reasons: (1) Context causes **re-renders for all consumers** when any value changes — Zustand uses selectors so only components reading the changed field re-render. (2) Context requires a Provider in the React tree — Zustand works **outside React**, which we need for axios interceptors. (3) Zustand is 1KB with zero boilerplate; Context requires its own reducer pattern for complex state.

### Q4: "How does your caching strategy work?"

**A:** TanStack Query caches API responses by `queryKey` (e.g., `["analytics", "dashboard"]`). Data is considered "fresh" for `staleTime` (5 min default, 30 min for analytics). During that window, navigating away and back shows cached data instantly — no loading spinner. When a mutation succeeds (e.g., creating a log), we call `invalidateQueries` to mark related caches as stale, triggering background refetch. The dashboard auto-refreshes when logs change.

---

## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 15d: Lambda Flows](./phase4-part15d-lambda-connections-and-flows.md) |
| ➡️ Next | [Part 16a: Setup, Config & Types](./phase4-part16a-frontend-setup-types.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**End of Phase 4 Part 16: Frontend Overview**
