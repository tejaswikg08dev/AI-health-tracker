# 🔌 Phase 4 Part 16b: Frontend — API Client & Services

> **"One axios instance with JWT interceptors and automatic token refresh. Eight service files — one per backend module — each exporting typed functions that call your FastAPI endpoints."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16a-frontend-setup-types.md](./phase4-part16a-frontend-setup-types.md) |
| **Next** | [phase4-part16c-frontend-store-hooks.md](./phase4-part16c-frontend-store-hooks.md) |
| **Files in This Doc** | 8 files (api.ts + 7 service files) |
| **Time to Type** | ~40 minutes |
| **Difficulty** | Hard (interceptors, token refresh queue, blob downloads) |

---

## 1. `src/services/api.ts` — Axios Instance + JWT Interceptors

This is the most important file in the frontend. Every API call flows through this single axios instance. It handles three things automatically:
1. **Attaches the JWT token** to every request (request interceptor)
2. **Catches 401 errors** and refreshes the token (response interceptor)
3. **Queues concurrent requests** during refresh so only one refresh call is made

### Type This Code:

```typescript
// ============================================================================
// API Client — Axios Instance with Auth Interceptors
// ============================================================================

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

// Create axios instance with defaults
const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 second timeout
});

// ── Request Interceptor: Attach JWT Token ──
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Handle 401 + Auto Refresh ──
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (token) {
      prom.resolve(token);
    } else {
      prom.reject(error);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // If 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Don't retry refresh or login endpoints (infinite loop prevention)
      if (
        originalRequest.url?.includes("/auth/refresh") ||
        originalRequest.url?.includes("/auth/login")
      ) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Another request is already refreshing — queue this one
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) {
          throw new Error("No refresh token");
        }

        // Call refresh endpoint
        const { data } = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          null,
          { params: { refresh_token: refreshToken } }
        );

        // Store new tokens
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);

        // Retry failed requests with new token
        processQueue(null, data.access_token);

        // Retry original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // Refresh failed — clear tokens and redirect to login
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

### How Token Refresh Works (Visual)

```
Request 1 → GET /habits → 401 (token expired)
  │
  ├─ isRefreshing = false → Set isRefreshing = true
  │   └─ POST /auth/refresh → 200 → New tokens saved
  │       └─ Retry Request 1 with new token → 200 ✅
  │
Request 2 → GET /analytics → 401 (same expired token)
  │
  ├─ isRefreshing = true → Add to failedQueue
  │   └─ (waits...)
  │       └─ processQueue() → Retry Request 2 with new token → 200 ✅
  │
Request 3 → GET /streaks → 401
  │
  ├─ isRefreshing = true → Add to failedQueue
  │   └─ (waits...)
  │       └─ processQueue() → Retry Request 3 with new token → 200 ✅

Result: 3 failed requests, only 1 refresh call, all 3 retried successfully.
User sees nothing — the refresh is invisible.
```

### Key: Why `axios.post` (Not `api.post`) for Refresh

```typescript
const { data } = await axios.post(         // ← raw axios, NOT our `api` instance
  `${API_BASE_URL}/api/v1/auth/refresh`,
  ...
);
```

If we used `api.post` for the refresh call, the response interceptor would catch any error and try to refresh AGAIN — **infinite loop**. Using raw `axios` bypasses our interceptors entirely.

### Key: `_retry` Flag Prevents Infinite Retries

```typescript
const originalRequest = error.config as InternalAxiosRequestConfig & {
  _retry?: boolean;   // Custom flag we add
};
if (error.response?.status === 401 && !originalRequest._retry) {
  originalRequest._retry = true;  // Mark it — only retry once
```

Without this flag, if the refreshed token is also invalid, we'd loop forever: 401 → refresh → 401 → refresh → ...

---

## 2. `src/services/auth.service.ts`

```typescript
import api from "./api";
import type { AuthTokens, LoginRequest, SignupRequest, User, UserUpdate } from "@/types/user";

export const authService = {
  async login(data: LoginRequest): Promise<AuthTokens> {
    const res = await api.post<AuthTokens>("/auth/login", data);
    return res.data;
  },

  async signup(data: SignupRequest): Promise<User> {
    const res = await api.post<User>("/auth/signup", data);
    return res.data;
  },

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const res = await api.post<AuthTokens>("/auth/refresh", null, {
      params: { refresh_token: refreshToken },
    });
    return res.data;
  },

  async logout(): Promise<void> {
    await api.post("/auth/logout");
  },

  async getProfile(): Promise<User> {
    const res = await api.get<User>("/auth/me");
    return res.data;
  },

  async updateProfile(data: UserUpdate): Promise<User> {
    const res = await api.put<User>("/auth/me", data);
    return res.data;
  },
};
```

**Pattern:** Every service is an object with `async` methods. Each method:
1. Calls `api.get/post/put/delete` with a typed generic (`<AuthTokens>`)
2. Returns `res.data` (the JSON body, not the full axios response)

**`api.post<AuthTokens>("/auth/login", data)`** — The generic `<AuthTokens>` tells TypeScript that `res.data` is of type `AuthTokens`. Without it, `res.data` would be `any`.

---

## 3. `src/services/habit.service.ts`

```typescript
import api from "./api";
import type { Habit, HabitCreate, HabitReorderRequest, HabitUpdate } from "@/types/habit";
import type { SuccessResponse } from "@/types/common";

export const habitService = {
  async getHabits(includeArchived = false): Promise<Habit[]> {
    const res = await api.get<Habit[]>("/habits", {
      params: { include_archived: includeArchived },
    });
    return res.data;
  },

  async getHabit(id: string): Promise<Habit> {
    const res = await api.get<Habit>(`/habits/${id}`);
    return res.data;
  },

  async createHabit(data: HabitCreate): Promise<Habit> {
    const res = await api.post<Habit>("/habits", data);
    return res.data;
  },

  async updateHabit(id: string, data: HabitUpdate): Promise<Habit> {
    const res = await api.put<Habit>(`/habits/${id}`, data);
    return res.data;
  },

  async deleteHabit(id: string): Promise<SuccessResponse> {
    const res = await api.delete<SuccessResponse>(`/habits/${id}`);
    return res.data;
  },

  async reorderHabits(data: HabitReorderRequest): Promise<Habit[]> {
    const res = await api.put<Habit[]>("/habits/reorder", data);
    return res.data;
  },
};
```

**`params: { include_archived: includeArchived }`** — Axios converts this to a query string: `GET /habits?include_archived=true`. Same as Python's `requests.get(url, params={...})`.

---

## 4. `src/services/log.service.ts`

```typescript
import api from "./api";
import type { BulkLogCreate, HabitLog, LogCreate, LogUpdate } from "@/types/log";
import type { SuccessResponse } from "@/types/common";

export const logService = {
  async createLog(data: LogCreate): Promise<HabitLog> {
    const res = await api.post<HabitLog>("/logs", data);
    return res.data;
  },

  async bulkCreateLogs(data: BulkLogCreate): Promise<HabitLog[]> {
    const res = await api.post<HabitLog[]>("/logs/bulk", data);
    return res.data;
  },

  async getLogsByDate(date: string): Promise<HabitLog[]> {
    const res = await api.get<HabitLog[]>("/logs", { params: { date } });
    return res.data;
  },

  async getLogsByRange(start: string, end: string, habitId?: string): Promise<HabitLog[]> {
    const res = await api.get<HabitLog[]>("/logs", {
      params: { start, end, habit_id: habitId },
    });
    return res.data;
  },

  async updateLog(id: string, data: LogUpdate): Promise<HabitLog> {
    const res = await api.put<HabitLog>(`/logs/${id}`, data);
    return res.data;
  },

  async deleteLog(id: string): Promise<SuccessResponse> {
    const res = await api.delete<SuccessResponse>(`/logs/${id}`);
    return res.data;
  },
};
```

**`bulkCreateLogs`** — The daily check-in page sends all habits in one request. This maps to `POST /logs/bulk` (Part 06b).

---

## 5. `src/services/analytics.service.ts`

```typescript
import api from "./api";
import type {
  AllStreaksResponse,
  CompletionRateResponse,
  CorrelationResponse,
  DashboardData,
  MonthlyTrendResponse,
  WeeklySummaryResponse,
} from "@/types/analytics";

export const analyticsService = {
  async getDashboard(): Promise<DashboardData> {
    const res = await api.get<DashboardData>("/analytics/dashboard");
    return res.data;
  },

  async getStreaks(): Promise<AllStreaksResponse> {
    const res = await api.get<AllStreaksResponse>("/analytics/streaks");
    return res.data;
  },

  async getWeeklySummary(): Promise<WeeklySummaryResponse> {
    const res = await api.get<WeeklySummaryResponse>("/analytics/weekly-summary");
    return res.data;
  },

  async getMonthlyTrend(habitId?: string, days = 30): Promise<MonthlyTrendResponse> {
    const res = await api.get<MonthlyTrendResponse>("/analytics/monthly-trend", {
      params: { habit_id: habitId, days },
    });
    return res.data;
  },

  async getCompletionRate(days = 30): Promise<CompletionRateResponse> {
    const res = await api.get<CompletionRateResponse>("/analytics/completion-rate", {
      params: { days },
    });
    return res.data;
  },

  async getCorrelations(days = 30): Promise<CorrelationResponse> {
    const res = await api.get<CorrelationResponse>("/analytics/correlations", {
      params: { days },
    });
    return res.data;
  },
};
```

**6 endpoints** — one for each analytics feature from Part 07. The `days` parameter with default `30` lets the frontend request different time ranges.

---

## 6. `src/services/ai.service.ts`

```typescript
import api from "./api";
import type {
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  DocumentInfo,
  DocumentListResponse,
  InsightData,
  InsightListResponse,
} from "@/types/ai";
import type { SuccessResponse } from "@/types/common";

export const aiService = {
  async chat(data: ChatRequest): Promise<ChatResponse> {
    const res = await api.post<ChatResponse>("/ai/chat", data);
    return res.data;
  },

  // SSE streaming chat — returns an EventSource-like reader
  streamChat(message: string): EventSource {
    const token = localStorage.getItem("access_token");
    const baseUrl = import.meta.env.VITE_API_URL || "";
    const url = `${baseUrl}/api/v1/ai/chat/stream?message=${encodeURIComponent(message)}`;
    return new EventSource(url);
  },

  async getChatHistory(): Promise<ChatHistoryResponse> {
    const res = await api.get<ChatHistoryResponse>("/ai/chat/history");
    return res.data;
  },

  async uploadDocument(file: File): Promise<DocumentInfo> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post<DocumentInfo>("/ai/documents", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000, // 2 min timeout for large files
    });
    return res.data;
  },

  async getDocuments(): Promise<DocumentListResponse> {
    const res = await api.get<DocumentListResponse>("/ai/documents");
    return res.data;
  },

  async deleteDocument(id: string): Promise<SuccessResponse> {
    const res = await api.delete<SuccessResponse>(`/ai/documents/${id}`);
    return res.data;
  },

  async generateInsight(): Promise<InsightData> {
    const res = await api.post<InsightData>("/ai/insights");
    return res.data;
  },

  async getInsights(): Promise<InsightListResponse> {
    const res = await api.get<InsightListResponse>("/ai/insights");
    return res.data;
  },

  async generateWeeklyReport(): Promise<InsightData> {
    const res = await api.post<InsightData>("/ai/weekly-report");
    return res.data;
  },
};
```

### Key: File Upload with FormData

```typescript
async uploadDocument(file: File): Promise<DocumentInfo> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post<DocumentInfo>("/ai/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return res.data;
},
```

- `new FormData()` — Browser API for sending files (not JSON)
- `"Content-Type": "multipart/form-data"` — overrides our default `application/json`
- `timeout: 120000` — 2 minutes instead of 30 seconds (large PDFs take time)
- Backend receives this as `UploadFile` in FastAPI (Part 12b)

### Key: SSE Streaming

```typescript
streamChat(message: string): EventSource {
  const token = localStorage.getItem("access_token");
  const baseUrl = import.meta.env.VITE_API_URL || "";
  const url = `${baseUrl}/api/v1/ai/chat/stream?message=${encodeURIComponent(message)}`;
  return new EventSource(url);
},
```

- `EventSource` is a browser API for Server-Sent Events
- Unlike `fetch`, EventSource keeps the connection open and receives chunks
- Note: EventSource doesn't support custom headers — the JWT token would need to be passed as a query param (or use `fetch` with `ReadableStream` in production)

---

## 7. `src/services/notification.service.ts`

```typescript
import api from "./api";
import type { NotificationSettings, NotificationSettingsUpdate } from "@/types/notification";
import type { SuccessResponse } from "@/types/common";

export const notificationService = {
  async getSettings(): Promise<NotificationSettings> {
    const res = await api.get<NotificationSettings>("/notifications/settings");
    return res.data;
  },

  async updateSettings(data: NotificationSettingsUpdate): Promise<NotificationSettings> {
    const res = await api.put<NotificationSettings>("/notifications/settings", data);
    return res.data;
  },

  async sendTestEmail(): Promise<SuccessResponse> {
    const res = await api.post<SuccessResponse>("/notifications/test-email", {
      email_type: "daily_reminder",
    });
    return res.data;
  },
};
```

---

## 8. `src/services/export.service.ts`

```typescript
import api from "./api";

export const exportService = {
  async exportCsv(startDate: string, endDate: string): Promise<Blob> {
    const res = await api.post(
      "/export/csv",
      { start_date: startDate, end_date: endDate },
      { responseType: "blob" }
    );
    return res.data;
  },

  async exportCsvToS3(startDate: string, endDate: string): Promise<{ download_url: string }> {
    const res = await api.post("/export/csv/s3", {
      start_date: startDate,
      end_date: endDate,
    });
    return res.data;
  },

  // Helper: trigger browser download from blob
  downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};
```

### Key: Blob Download Pattern

```typescript
async exportCsv(...): Promise<Blob> {
  const res = await api.post("/export/csv", data, { responseType: "blob" });
  return res.data;  // This is a Blob, not JSON
},

downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);  // Create temporary URL
  const a = document.createElement("a");          // Create invisible <a> tag
  a.href = url;
  a.download = filename;                          // Set download filename
  document.body.appendChild(a);
  a.click();                                      // Trigger download
  document.body.removeChild(a);                   // Clean up
  window.URL.revokeObjectURL(url);                // Release memory
},
```

- `responseType: "blob"` tells axios to treat the response as binary data, not JSON
- `createObjectURL` creates a temporary browser URL pointing to the blob in memory
- Creating and clicking an `<a>` tag triggers the browser's "Save As" dialog
- This is the standard pattern for downloading files from APIs in SPAs

---

## 9. Service → Backend Endpoint Map

| Service | Method | HTTP | Backend Endpoint |
|---------|--------|------|-----------------|
| auth | `login` | POST | `/auth/login` (Part 04) |
| auth | `signup` | POST | `/auth/signup` (Part 04) |
| auth | `getProfile` | GET | `/auth/me` (Part 04) |
| habit | `getHabits` | GET | `/habits` (Part 05) |
| habit | `createHabit` | POST | `/habits` (Part 05) |
| habit | `deleteHabit` | DELETE | `/habits/{id}` (Part 05) |
| log | `bulkCreateLogs` | POST | `/logs/bulk` (Part 06) |
| log | `getLogsByDate` | GET | `/logs?date=` (Part 06) |
| analytics | `getDashboard` | GET | `/analytics/dashboard` (Part 07) |
| analytics | `getStreaks` | GET | `/analytics/streaks` (Part 07) |
| analytics | `getCorrelations` | GET | `/analytics/correlations` (Part 07) |
| ai | `chat` | POST | `/ai/chat` (Part 12) |
| ai | `uploadDocument` | POST | `/ai/documents` (Part 12) |
| notification | `getSettings` | GET | `/notifications/settings` (Part 13) |
| export | `exportCsv` | POST | `/export/csv` (Part 14) |

---

## 10. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Axios interceptors** | api.ts — auto-attach JWT to every request |
| 2 | **Token refresh queue** | api.ts — queue concurrent 401s, one refresh call |
| 3 | **`_retry` flag** | api.ts — prevent infinite retry loops |
| 4 | **Raw axios for refresh** | api.ts — bypass interceptors to avoid loops |
| 5 | **Typed generics** | `api.get<Habit[]>` → res.data is `Habit[]` |
| 6 | **FormData file upload** | ai.service — `multipart/form-data` for PDFs |
| 7 | **Blob download** | export.service — `createObjectURL` + invisible `<a>` |
| 8 | **Service object pattern** | All services — plain objects with async methods |

---

## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16a: Setup & Types](./phase4-part16a-frontend-setup-types.md) |
| ➡️ Next | [Part 16c: Store & Hooks](./phase4-part16c-frontend-store-hooks.md) |

---

**End of Phase 4 Part 16b: API Client & Services**
