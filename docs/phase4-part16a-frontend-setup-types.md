# 🛠️ Phase 4 Part 16a: Frontend — Setup, Config & TypeScript Types

> **"The foundation: package.json declares 14 dependencies, Vite configures the dev server with API proxy, TypeScript enforces strict mode with path aliases, Tailwind adds brand colors, and 7 type files mirror every backend Pydantic schema."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16-frontend-overview.md](./phase4-part16-frontend-overview.md) |
| **Next** | [phase4-part16b-frontend-api-client-services.md](./phase4-part16b-frontend-api-client-services.md) |
| **Files in This Doc** | 12 files (4 config + 1 CSS + 7 type files) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Easy (mostly configuration + interface definitions) |

---

## 1. `package.json` — Dependencies & Scripts

### Type This Code:

```json
{
  "name": "health-tracker-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "@tanstack/react-query": "^5.56.2",
    "axios": "^1.7.7",
    "zustand": "^4.5.5",
    "recharts": "^2.12.7",
    "react-hook-form": "^7.53.0",
    "@hookform/resolvers": "^3.9.0",
    "zod": "^3.23.8",
    "date-fns": "^3.6.0",
    "lucide-react": "^0.441.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.10.0",
    "postcss": "^8.4.45",
    "tailwindcss": "^3.4.11",
    "typescript": "^5.5.4",
    "vite": "^5.4.5"
  }
}
```

### Line-by-Line Explanation

**`"type": "module"`** — Tells Node.js to use ES modules (`import/export`) instead of CommonJS (`require`). Vite requires this.

**Scripts:**
- `"dev": "vite"` — Starts the dev server on port 3000 with hot reload
- `"build": "tsc -b && vite build"` — First TypeScript checks types, then Vite bundles for production
- `"lint": "eslint ."` — Runs ESLint on all files
- `"preview": "vite preview"` — Preview the production build locally

**Dependencies (14):**

| Package | Purpose |
|---------|---------|
| `react`, `react-dom` | Core UI library |
| `react-router-dom` | Client-side routing (8 routes) |
| `@tanstack/react-query` | Server state: caching, loading, refetch |
| `axios` | HTTP client with interceptors |
| `zustand` | Client state: auth store (1KB vs Redux 10KB) |
| `recharts` | Charts: bar, line, pie (built on D3) |
| `react-hook-form` | Form handling with minimal re-renders |
| `@hookform/resolvers` | Connects react-hook-form to Zod |
| `zod` | Schema validation (TypeScript-first) |
| `date-fns` | Date utilities (modular imports) |
| `lucide-react` | 1000+ SVG icons as React components |
| `clsx` | Conditional CSS class names |
| `tailwind-merge` | Deduplicates conflicting Tailwind classes |

**Dev Dependencies (8):**

| Package | Purpose |
|---------|---------|
| `@types/react`, `@types/react-dom` | TypeScript type definitions for React |
| `@vitejs/plugin-react` | Vite plugin for React (JSX transform, Fast Refresh) |
| `autoprefixer` | Adds browser vendor prefixes to CSS |
| `eslint` | Code linting |
| `postcss` | CSS processing pipeline (required by Tailwind) |
| `tailwindcss` | Utility-first CSS framework |
| `typescript` | TypeScript compiler |
| `vite` | Build tool + dev server |

---

## 2. `vite.config.ts` — Build Tool Configuration

### Type This Code:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    // Enable @ path alias: import { Button } from "@/components/ui/Button"
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    // Proxy API requests to the backend during development.
    // This avoids CORS issues: frontend (:3000) → backend (:8000)
    // In production, Nginx handles this routing.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

### Key Details

**`plugins: [react()]`** — Enables React Fast Refresh (hot reload without losing component state) and automatic JSX transform (no need for `import React` at the top of every file).

**`alias: { "@": ... }`** — Path aliases. Instead of writing `import { cn } from "../../../lib/utils"` (counting `../` levels), you write `import { cn } from "@/lib/utils"`. The `@` always means `src/`.

**`proxy: { "/api": ... }`** — During development:
- Frontend runs on `http://localhost:3000`
- Backend runs on `http://localhost:8000`
- Without proxy: browser blocks cross-origin requests (CORS)
- With proxy: browser sends to `:3000/api/v1/habits` → Vite forwards to `:8000/api/v1/habits`
- The browser thinks it's same-origin. No CORS errors.

---

## 3. `tsconfig.json` — TypeScript Configuration

### Type This Code:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting — strict mode catches bugs early */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,

    /* Path aliases — import from @/ instead of ../../../ */
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

### Key Details

**`"strict": true`** — Enables ALL TypeScript strict checks:
- `strictNullChecks` — `string` and `string | null` are different types (no surprise `undefined`)
- `strictFunctionTypes` — function parameter types must match exactly
- `noImplicitAny` — every variable must have a type (no hidden `any`)

**`"paths": { "@/*": ["./src/*"] }`** — Must match the Vite alias. TypeScript and Vite both need to know that `@/` means `src/`.

**`"jsx": "react-jsx"`** — Uses the modern JSX transform. You don't need to write `import React from "react"` at the top of every `.tsx` file.

**`"noEmit": true`** — TypeScript only checks types, doesn't produce JavaScript. Vite handles the actual compilation (it's faster).

---

## 4. `tailwind.config.js` — Styling

### Type This Code:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Custom brand colors for the health tracker
        brand: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",  // Primary blue
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
```

### Key Details

**`content: [...]`** — Tailwind scans these files for class names. Only classes actually used in your code end up in the final CSS. Unused classes like `bg-pink-700` are removed (tree-shaking).

**Custom brand colors** — `brand-500` is the primary blue (`#3B82F6`). You use it everywhere: `bg-brand-600`, `text-brand-500`, `ring-brand-500`. The 50–900 scale gives you shades from lightest to darkest.

**Why extend, not replace?** `theme.extend.colors` ADDS brand colors alongside Tailwind's defaults (gray, red, green...). If you used `theme.colors` instead, you'd lose ALL default colors.

---

## 5. `src/index.css` — Global Styles

### Type This Code:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Global styles */
body {
  @apply bg-gray-50 min-h-screen;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  @apply bg-transparent;
}
::-webkit-scrollbar-thumb {
  @apply bg-gray-300 rounded-full;
}
::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400;
}
```

**`@tailwind base/components/utilities`** — These three directives inject Tailwind's CSS. PostCSS processes them into real CSS at build time.

**`@apply`** — Lets you use Tailwind classes inside CSS files. `@apply bg-gray-50` becomes `background-color: rgb(249 250 251)`.

---

## 6. TypeScript Types (7 Files)

These files mirror your backend Pydantic schemas. Every interface here matches a schema from Parts 04–13.

### 6.1 `src/types/common.ts`

```typescript
// ============================================================================
// Common TypeScript Types — shared across all modules
// ============================================================================

export interface ApiError {
  error_code: string;
  message: string;
  detail: string | string[] | null;
}

export interface SuccessResponse {
  message: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
```

**`PaginatedResponse<T>`** — This is a **generic type**. `T` is a placeholder. `PaginatedResponse<Habit>` means `items` is `Habit[]`. Same as Python's `list[Habit]` but enforced at compile time.

**`detail: string | string[] | null`** — A **union type**. The detail field can be a string ("invalid email"), an array of strings (FastAPI validation errors), or null. TypeScript forces you to check which one it is before using it.

---

### 6.2 `src/types/user.ts`

```typescript
// ============================================================================
// User & Auth Types — mirrors backend auth schemas
// ============================================================================

export interface User {
  id: string;
  email: string;
  full_name: string;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  full_name: string;
  timezone?: string;
}

export interface UserUpdate {
  full_name?: string;
  timezone?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
```

**`timezone?: string`** — The `?` makes this field **optional**. In Python (Pydantic), this was `timezone: str | None = None`. TypeScript uses `?` for the same concept.

**Backend mirror:**
| TypeScript | Python Pydantic |
|-----------|----------------|
| `LoginRequest` | `LoginRequest` (Part 04b) |
| `AuthTokens` | `TokenResponse` (Part 04b) |
| `User` | `UserRead` (Part 04b) |

---

### 6.3 `src/types/habit.ts`

```typescript
// ============================================================================
// Habit Types — mirrors backend habit schemas
// ============================================================================

export type HabitType = "numeric" | "boolean" | "scale";

export interface Habit {
  id: string;
  name: string;
  habit_type: HabitType;
  unit: string;
  target_value: number | null;
  color: string;
  icon: string;
  sort_order: number;
  is_archived: boolean;
  created_at: string;
}

export interface HabitCreate {
  name: string;
  habit_type: HabitType;
  unit?: string;
  target_value?: number | null;
  color?: string;
  icon?: string;
}

export interface HabitUpdate {
  name?: string;
  unit?: string;
  target_value?: number | null;
  color?: string;
  icon?: string;
}

export interface HabitReorderRequest {
  habit_ids: string[];
}

// Predefined colors and icons for the habit creation form
export const HABIT_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
  "#EC4899", "#06B6D4", "#F97316", "#6366F1", "#14B8A6",
];

export const HABIT_ICONS = [
  "💧", "😴", "🏃", "😊", "📖", "🧘", "💊", "🥗",
  "🎯", "⭐", "💪", "🧠", "🌙", "☀️", "❤️", "🏋️",
];
```

**`type HabitType = "numeric" | "boolean" | "scale"`** — A **string literal union**. The variable can ONLY be one of these three strings. If you accidentally write `"number"`, TypeScript gives a compile error. In Python, this was `Literal["numeric", "boolean", "scale"]`.

**`HABIT_COLORS` and `HABIT_ICONS`** — These are `const` values (not interfaces) — exported from a type file because the HabitForm component needs them for the color/icon picker. They're arrays of predefined choices.

---

### 6.4 `src/types/log.ts`

```typescript
// ============================================================================
// Habit Log Types — mirrors backend log schemas
// ============================================================================

export interface HabitLog {
  id: string;
  habit_id: string;
  log_date: string;          // "2026-09-26"
  value_numeric: number | null;
  value_boolean: boolean | null;
  value_scale: number | null;
  notes: string | null;
  created_at: string;
}

export interface LogCreate {
  habit_id: string;
  log_date: string;
  value_numeric?: number | null;
  value_boolean?: boolean | null;
  value_scale?: number | null;
  notes?: string | null;
}

export interface BulkLogEntry {
  habit_id: string;
  value_numeric?: number | null;
  value_boolean?: boolean | null;
  value_scale?: number | null;
  notes?: string | null;
}

export interface BulkLogCreate {
  log_date: string;
  entries: BulkLogEntry[];
}

export interface LogUpdate {
  value_numeric?: number | null;
  value_boolean?: boolean | null;
  value_scale?: number | null;
  notes?: string | null;
}
```

**`BulkLogCreate`** — The daily check-in sends ALL habits at once. Instead of 6 individual POST requests (one per habit), we send 1 bulk request with an array of entries. This matches the `POST /logs/bulk` endpoint from Part 06b.

**`log_date: string`** — Dates are strings in TypeScript (`"2026-09-26"`), not Date objects. The backend expects ISO format strings, so we keep them as strings throughout.

---

### 6.5 `src/types/analytics.ts`

```typescript
// ============================================================================
// Analytics Types — mirrors backend analytics schemas
// ============================================================================

export interface DashboardData {
  today_logged: number;
  today_total: number;
  today_completion_pct: number;
  total_active_habits: number;
  current_best_streak: StreakInfo | null;
  week_completion_pct: number;
}

export interface StreakInfo {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  habit_icon: string;
  current_streak: number;
  longest_streak: number;
  last_logged_date: string | null;
}

export interface AllStreaksResponse {
  streaks: StreakInfo[];
}

export interface HabitWeeklySummary {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  this_week_avg: number | null;
  last_week_avg: number | null;
  change_pct: number | null;
  this_week_count: number;
  last_week_count: number;
}

export interface WeeklySummaryResponse {
  week_start: string;
  week_end: string;
  habits: HabitWeeklySummary[];
}

export interface TrendDataPoint {
  date: string;
  value: number | null;
}

export interface HabitTrendData {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  habit_type: string;
  data_points: TrendDataPoint[];
}

export interface MonthlyTrendResponse {
  start_date: string;
  end_date: string;
  habits: HabitTrendData[];
}

export interface HabitCompletionRate {
  habit_id: string;
  habit_name: string;
  habit_color: string;
  habit_icon: string;
  days_logged: number;
  total_days: number;
  completion_pct: number;
}

export interface CompletionRateResponse {
  period_start: string;
  period_end: string;
  habits: HabitCompletionRate[];
}

export interface CorrelationResult {
  habit_a_id: string;
  habit_a_name: string;
  habit_b_id: string;
  habit_b_name: string;
  correlation: number;
  strength: string;
  direction: string;
  data_points: number;
  insight: string;
}

export interface CorrelationResponse {
  correlations: CorrelationResult[];
}
```

**This is the largest type file** — analytics has 6 endpoints, each with its own response type. These match the schemas from Part 07b (Analytics router).

**Nested types:** `MonthlyTrendResponse` contains `HabitTrendData[]`, which contains `TrendDataPoint[]`. Three levels of nesting — TypeScript ensures you navigate them correctly.

---

### 6.6 `src/types/ai.ts`

```typescript
// ============================================================================
// AI Types — chat, documents, insights
// ============================================================================

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tokens_used: number;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  use_agent?: boolean;
}

export interface ChatResponse {
  response: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number | null;
  status: "uploaded" | "processing" | "processed" | "failed";
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
}

export interface InsightData {
  id: string;
  insight_type: string;
  title: string;
  content: string;
  tokens_used: number;
  created_at: string;
}

export interface InsightListResponse {
  insights: InsightData[];
}
```

**`role: "user" | "assistant"`** — String literal union again. Chat messages can only be from the user or the assistant. No other values allowed.

**`status: "uploaded" | "processing" | "processed" | "failed"`** — A **state machine as a type**. Document processing goes through these 4 states. TypeScript ensures you handle all cases.

---

### 6.7 `src/types/notification.ts`

```typescript
// ============================================================================
// Notification Types
// ============================================================================

export interface NotificationSettings {
  id: string;
  daily_reminder: boolean;
  weekly_report: boolean;
  streak_alerts: boolean;
  reminder_time: string;    // "HH:MM"
  created_at: string;
}

export interface NotificationSettingsUpdate {
  daily_reminder?: boolean;
  weekly_report?: boolean;
  streak_alerts?: boolean;
  reminder_time?: string;
}
```

The simplest type file — notification settings are just toggles and a time string.

---

## 7. How Types Connect Backend → Frontend

```
BACKEND (Python)                    FRONTEND (TypeScript)
─────────────────                   ────────────────────
class HabitCreate(BaseModel):  ──►  interface HabitCreate {
    name: str                           name: string;
    habit_type: Literal[...]            habit_type: HabitType;
    unit: str | None = None             unit?: string;
                                    }

class HabitRead(BaseModel):    ──►  interface Habit {
    id: UUID                            id: string;
    name: str                           name: string;
    created_at: datetime                created_at: string;
                                    }
```

**Key differences:**
| Python | TypeScript | Why |
|--------|-----------|-----|
| `UUID` | `string` | JSON serializes UUIDs as strings |
| `datetime` | `string` | JSON serializes dates as ISO strings |
| `str \| None = None` | `field?: string` | Optional fields use `?` |
| `Literal["a", "b"]` | `"a" \| "b"` | String literal unions |
| `list[Habit]` | `Habit[]` | Array syntax |

---

## 8. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **`"type": "module"`** | package.json — ES modules for Vite |
| 2 | **Vite proxy** | vite.config.ts — `/api` → `:8000` avoids CORS |
| 3 | **Path alias `@/`** | vite.config + tsconfig — both must match |
| 4 | **`strict: true`** | tsconfig — all TypeScript strict checks |
| 5 | **`@tailwind` directives** | index.css — Tailwind CSS injection |
| 6 | **Generic types `<T>`** | PaginatedResponse<T> — reusable container |
| 7 | **String literal unions** | HabitType, role, status — restricted values |
| 8 | **Optional fields `?`** | Mirrors Pydantic `= None` defaults |
| 9 | **Backend ↔ Frontend type mapping** | UUID → string, datetime → string |
| 10 | **`const` exports** | HABIT_COLORS, HABIT_ICONS — shared constants |

---

## 9. Interview Questions

### Q1: "Why TypeScript instead of JavaScript?"

**A:** TypeScript catches bugs at compile time that JavaScript only catches at runtime. If the backend changes a field name from `full_name` to `fullName`, TypeScript shows errors in every file that uses the old name — before any user sees a bug. In a 50-file frontend, this saves hours of debugging. The trade-off is initial setup time, but Vite handles that automatically.

### Q2: "Why not generate types from the backend automatically?"

**A:** Tools like `openapi-typescript` can generate TypeScript interfaces from an OpenAPI spec. We wrote them manually for two reasons: (1) the project is small enough that manual sync is manageable, and (2) writing types by hand teaches you how frontend-backend contracts work. In a large team with 100+ endpoints, auto-generation is the right call.

### Q3: "What does the Vite proxy do and why is it needed?"

**A:** Browsers enforce **Same-Origin Policy** — JavaScript on `localhost:3000` cannot call `localhost:8000` directly (different ports = different origins). The proxy makes the browser think the API is on the same origin. Vite intercepts `/api` requests and forwards them to the backend. In production, Nginx does this same routing — the frontend never calls the backend directly.

---

## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16: Frontend Overview](./phase4-part16-frontend-overview.md) |
| ➡️ Next | [Part 16b: API Client & Services](./phase4-part16b-frontend-api-client-services.md) |

---

**End of Phase 4 Part 16a: Setup, Config & Types**
