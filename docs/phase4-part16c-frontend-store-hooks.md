# 🧠 Phase 4 Part 16c: Frontend — Zustand Store & TanStack Query Hooks

> **"One Zustand store manages auth globally (login, logout, tokens in localStorage). Four TanStack Query hook files provide auto-cached, auto-refetching data access to habits, logs, analytics, and AI chat — replacing 200+ lines of useState/useEffect boilerplate."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16b-frontend-api-client-services.md](./phase4-part16b-frontend-api-client-services.md) |
| **Next** | [phase4-part16d-frontend-layout-components.md](./phase4-part16d-frontend-layout-components.md) |
| **Files in This Doc** | 5 files (1 store + 4 hook files) |
| **Time to Type** | ~35 minutes |
| **Difficulty** | Medium (Zustand create, useQuery/useMutation, cache invalidation) |

---

## 1. `src/store/auth-store.ts` — Zustand Global Auth State

### Type This Code:

```typescript
// ============================================================================
// Auth Store — Zustand (Global State Management)
// ============================================================================

import { create } from "zustand";
import type { User, AuthTokens } from "@/types/user";
import { authService } from "@/services/auth.service";

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string, timezone?: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // ── Initial State ──
  // Check localStorage for existing session on app load
  user: (() => {
    try {
      const stored = localStorage.getItem("user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  })(),
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: false,

  // ── Login ──
  login: async (email, password) => {
    set({ isLoading: true });
    try {
      // Get tokens from API
      const tokens = await authService.login({ email, password });

      // Store tokens
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);

      // Fetch user profile
      const user = await authService.getProfile();
      localStorage.setItem("user", JSON.stringify(user));

      set({ user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error; // Re-throw so the login page can show the error
    }
  },

  // ── Signup ──
  signup: async (email, password, fullName, timezone) => {
    set({ isLoading: true });
    try {
      await authService.signup({ email, password, full_name: fullName, timezone });
      // After signup, auto-login
      await get().login(email, password);
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  // ── Logout ──
  logout: async () => {
    try {
      await authService.logout();
    } catch {
      // Ignore logout API errors — we're clearing local state anyway
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      set({ user: null, isAuthenticated: false });
    }
  },

  // ── Load User (on app startup if token exists) ──
  loadUser: async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ user: null, isAuthenticated: false });
      return;
    }

    try {
      const user = await authService.getProfile();
      localStorage.setItem("user", JSON.stringify(user));
      set({ user, isAuthenticated: true });
    } catch {
      // Token is invalid — clear everything
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      set({ user: null, isAuthenticated: false });
    }
  },

  // ── Set User (after profile update) ──
  setUser: (user) => {
    localStorage.setItem("user", JSON.stringify(user));
    set({ user });
  },
}));
```

### How Zustand Works

```typescript
// CREATE the store — one function call
export const useAuthStore = create<AuthState>((set, get) => ({
  // state fields
  user: null,
  isAuthenticated: false,

  // action: update state with set()
  login: async (email, password) => {
    set({ isLoading: true });        // ← triggers re-render in subscribed components
    const tokens = await authService.login({ email, password });
    set({ user, isAuthenticated: true, isLoading: false });
  },
}));

// USE the store in any component — selector pattern
const { user, login } = useAuthStore();            // Subscribe to ALL fields
const isAuth = useAuthStore((s) => s.isAuthenticated); // Subscribe to ONE field
```

**`set()`** — Merges new values into state (like `setState` in React class components). When you call `set({ isLoading: true })`, only components subscribed to `isLoading` re-render.

**`get()`** — Access current state inside actions. Used in `signup` to call `get().login()` after account creation.

### Key: Hydration from localStorage

```typescript
user: (() => {
  try {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
})(),
isAuthenticated: !!localStorage.getItem("access_token"),
```

This runs ONCE when the store is created (app load). If the user previously logged in and refreshes the page:
- `localStorage` still has the token and user object
- The store initializes with `isAuthenticated: true` and the cached user
- No login screen flash — the user sees the dashboard immediately

**`!!`** — Double negation converts a value to boolean. `!!"some_token"` → `true`. `!!null` → `false`.

---

## 2. `src/hooks/useHabits.ts` — TanStack Query CRUD Hooks

### Type This Code:

```typescript
// ============================================================================
// useHabits — TanStack Query hooks for habit CRUD
// ============================================================================

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { habitService } from "@/services/habit.service";
import type { HabitCreate, HabitUpdate } from "@/types/habit";

// Query key constants — used for cache invalidation
const HABITS_KEY = ["habits"];

export function useHabits(includeArchived = false) {
  return useQuery({
    queryKey: [...HABITS_KEY, { includeArchived }],
    queryFn: () => habitService.getHabits(includeArchived),
  });
}

export function useHabit(id: string) {
  return useQuery({
    queryKey: [...HABITS_KEY, id],
    queryFn: () => habitService.getHabit(id),
    enabled: !!id, // Don't fetch if id is empty
  });
}

export function useCreateHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: HabitCreate) => habitService.createHabit(data),
    onSuccess: () => {
      // Invalidate habits cache — triggers refetch of the habit list
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}

export function useUpdateHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: HabitUpdate }) =>
      habitService.updateHabit(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}

export function useDeleteHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => habitService.deleteHabit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}

export function useReorderHabits() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (habitIds: string[]) =>
      habitService.reorderHabits({ habit_ids: habitIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}
```

### useQuery vs useMutation

```
useQuery  = READ data (GET requests)
  → Auto-fetches on mount
  → Auto-refetches on window focus
  → Returns { data, isLoading, error }
  → Cached by queryKey

useMutation = WRITE data (POST/PUT/DELETE requests)
  → Doesn't auto-run — you call mutate() or mutateAsync()
  → Returns { mutate, mutateAsync, isPending, error }
  → onSuccess: invalidate related caches
```

### Key: Cache Invalidation

```typescript
export function useCreateHabit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: HabitCreate) => habitService.createHabit(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HABITS_KEY });
    },
  });
}
```

When a habit is created:
1. `mutationFn` sends `POST /habits` → backend creates habit
2. `onSuccess` fires → `invalidateQueries({ queryKey: HABITS_KEY })`
3. TanStack Query marks ALL queries starting with `["habits"]` as stale
4. Any component using `useHabits()` automatically refetches → UI updates

**You never manually update the habit list.** The cache invalidation triggers a refetch, and the component re-renders with fresh data.

---

## 3. `src/hooks/useLogs.ts` — Cross-Module Cache Invalidation

### Type This Code:

```typescript
// useLog hooks — TanStack Query for daily check-ins

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { logService } from "@/services/log.service";
import type { BulkLogCreate, LogCreate, LogUpdate } from "@/types/log";

const LOGS_KEY = ["logs"];
const ANALYTICS_KEY = ["analytics"]; // Invalidate analytics when logs change

export function useLogsByDate(date: string) {
  return useQuery({
    queryKey: [...LOGS_KEY, "date", date],
    queryFn: () => logService.getLogsByDate(date),
    enabled: !!date,
  });
}

export function useLogsByRange(start: string, end: string, habitId?: string) {
  return useQuery({
    queryKey: [...LOGS_KEY, "range", start, end, habitId],
    queryFn: () => logService.getLogsByRange(start, end, habitId),
    enabled: !!start && !!end,
  });
}

export function useCreateLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: LogCreate) => logService.createLog(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}

export function useBulkCreateLogs() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkLogCreate) => logService.bulkCreateLogs(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}

export function useUpdateLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LogUpdate }) =>
      logService.updateLog(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}

export function useDeleteLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => logService.deleteLog(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LOGS_KEY });
      queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY });
    },
  });
}
```

### Key: Cross-Module Invalidation

```typescript
const ANALYTICS_KEY = ["analytics"];

onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: LOGS_KEY });      // Refetch logs
  queryClient.invalidateQueries({ queryKey: ANALYTICS_KEY }); // Refetch dashboard too!
},
```

When a user logs a habit, the **dashboard** data changes (today's progress, streaks, completion %). By invalidating `ANALYTICS_KEY`, the dashboard auto-refreshes even though the user is on the check-in page. When they navigate to the dashboard, fresh data is already loaded.

---

## 4. `src/hooks/useAnalytics.ts` — Stale Time Configuration

### Type This Code:

```typescript
// useAnalytics hooks — TanStack Query for dashboard, streaks, charts

import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";

const ANALYTICS_KEY = ["analytics"];

export function useDashboard() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "dashboard"],
    queryFn: () => analyticsService.getDashboard(),
    staleTime: 5 * 60 * 1000, // 5 min — matches backend cache TTL
  });
}

export function useStreaks() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "streaks"],
    queryFn: () => analyticsService.getStreaks(),
    staleTime: 30 * 60 * 1000, // 30 min
  });
}

export function useWeeklySummary() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "weekly"],
    queryFn: () => analyticsService.getWeeklySummary(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useMonthlyTrend(habitId?: string, days = 30) {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "monthly", habitId, days],
    queryFn: () => analyticsService.getMonthlyTrend(habitId, days),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

export function useCompletionRate(days = 30) {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "completion", days],
    queryFn: () => analyticsService.getCompletionRate(days),
    staleTime: 30 * 60 * 1000,
  });
}

export function useCorrelations(days = 30) {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, "correlations", days],
    queryFn: () => analyticsService.getCorrelations(days),
    staleTime: 60 * 60 * 1000,
  });
}
```

### Stale Time Strategy

| Hook | staleTime | Why |
|------|-----------|-----|
| `useDashboard` | 5 min | Changes frequently (today's progress) |
| `useStreaks` | 30 min | Streaks change once per day at most |
| `useWeeklySummary` | 30 min | Weekly data doesn't change mid-day |
| `useMonthlyTrend` | 1 hour | Historical data rarely changes |
| `useCorrelations` | 1 hour | Statistical analysis is expensive to compute |

**What staleTime means:** During this window, TanStack Query serves cached data WITHOUT calling the API. Navigation to the analytics page shows instant data. After the window expires, the next access triggers a background refetch.

---

## 5. `src/hooks/useChat.ts` — Custom Hook (Not TanStack Query)

### Type This Code:

```typescript
// ============================================================================
// useChat — Custom hook for AI chat with streaming support
// ============================================================================

import { useState, useCallback } from "react";
import { aiService } from "@/services/ai.service";
import type { ChatMessage } from "@/types/ai";

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (message: string, useAgent?: boolean) => Promise<void>;
  loadHistory: () => Promise<void>;
  clearMessages: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const data = await aiService.getChatHistory();
      setMessages(data.messages);
    } catch {
      // Chat history load failure is not critical
    }
  }, []);

  const sendMessage = useCallback(
    async (message: string, useAgent = true) => {
      setIsLoading(true);
      setError(null);

      // Add user message to UI immediately (optimistic)
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        tokens_used: 0,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        // Call the AI chat endpoint
        const response = await aiService.chat({
          message,
          use_agent: useAgent,
        });

        // Add assistant response
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.response,
          tokens_used: 0,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to get response";
        setError(errorMsg);

        // Add error message to chat
        const errorChat: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Sorry, I encountered an error: ${errorMsg}. Please try again.`,
          tokens_used: 0,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorChat]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    loadHistory,
    clearMessages,
  };
}
```

### Why a Custom Hook (Not TanStack Query)?

Chat doesn't fit the query/mutation pattern:
- **Messages are stateful** — you add user messages locally BEFORE the API responds (optimistic UI)
- **It's conversational** — not a simple "fetch data, show data" cycle
- **Error handling is inline** — errors become chat messages, not toast notifications

**`useCallback`** — Wraps functions so they don't get recreated on every render. Without `useCallback`, components that receive these functions as props would re-render unnecessarily.

**`crypto.randomUUID()`** — Generates a unique ID for each message in the browser. The server assigns its own IDs, but we need temporary IDs for React's `key` prop.

---

## 6. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Zustand `create()`** | auth-store — global state in one function |
| 2 | **`set()` and `get()`** | auth-store — update and read state in actions |
| 3 | **localStorage hydration** | auth-store — persist login across refreshes |
| 4 | **`useQuery`** | useHabits, useAnalytics — auto-fetch + cache |
| 5 | **`useMutation`** | useCreateHabit — POST/PUT/DELETE with side effects |
| 6 | **`invalidateQueries`** | All mutations — trigger automatic refetch |
| 7 | **Cross-module invalidation** | useLogs — log change invalidates analytics cache |
| 8 | **`staleTime`** | useAnalytics — control how long cached data is "fresh" |
| 9 | **`enabled` flag** | useLogsByDate — skip fetch if date is empty |
| 10 | **Custom hook vs TanStack** | useChat — stateful chat doesn't fit query pattern |
| 11 | **Optimistic UI** | useChat — user message appears before API responds |
| 12 | **`useCallback`** | useChat — prevent unnecessary re-renders |

---

## 7. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16b: API Client & Services](./phase4-part16b-frontend-api-client-services.md) |
| ➡️ Next | [Part 16d: Layout Components](./phase4-part16d-frontend-layout-components.md) |

---

**End of Phase 4 Part 16c: Store & Hooks**
