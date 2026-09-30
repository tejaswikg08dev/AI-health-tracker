# 🏗️ Phase 4 Part 16d: Frontend — Layout Components & Utilities

> **"Five layout components form the app shell: PageLayout composes Navbar + Sidebar + Outlet, ProtectedRoute guards auth, and utils.ts provides the cn() function used in every component."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part16c-frontend-store-hooks.md](./phase4-part16c-frontend-store-hooks.md) |
| **Next** | [phase4-part16e-frontend-feature-components.md](./phase4-part16e-frontend-feature-components.md) |
| **Files in This Doc** | 6 files (5 layout components + utils.ts) |
| **Time to Type** | ~25 minutes |
| **Difficulty** | Easy-Medium (React Router Outlet, Tailwind utility merge) |

---

## 1. `src/lib/utils.ts` — Shared Utility Functions

### Type This Code:

```typescript
// Utility functions used across the frontend

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * cn() — merge Tailwind CSS classes intelligently.
 *
 * Combines clsx (conditional classes) with tailwind-merge (dedup conflicting classes).
 * Example: cn("px-4 py-2", isActive && "bg-blue-500", "px-8")
 *   → "py-2 bg-blue-500 px-8" (px-4 is overridden by px-8)
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string for display.
 */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format a date as YYYY-MM-DD (for API calls).
 */
export function toDateString(date: Date): string {
  return date.toISOString().split("T")[0];
}

/**
 * Get today's date as YYYY-MM-DD.
 */
export function todayString(): string {
  return toDateString(new Date());
}

/**
 * Truncate text with ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

/**
 * Format file size (bytes → human-readable).
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
```

### Key: The `cn()` Function

```typescript
// Without cn(): classes conflict — which padding wins?
<div className="px-4 px-8">  // Both applied! Browser uses last one (maybe)

// With cn(): tailwind-merge resolves conflicts
<div className={cn("px-4", isWide && "px-8")}>  // → "px-8" (deduped)
```

`cn()` is the standard utility in **shadcn/ui** and most Tailwind projects. Two libraries work together:
- **clsx** — handles conditional classes: `clsx("a", false && "b", "c")` → `"a c"`
- **tailwind-merge** — deduplicates Tailwind conflicts: `twMerge("px-4 px-8")` → `"px-8"`

---

## 2. `src/components/layout/ProtectedRoute.tsx` — Auth Guard

### Type This Code:

```typescript
// Auth guard — redirects to login if not authenticated

import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Outlet renders the child route (DashboardPage, HabitsPage, etc.)
  return <Outlet />;
}
```

**How it works in the route tree:**
```
<Route element={<ProtectedRoute />}>     ← This is a "layout route"
  <Route element={<PageLayout />}>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/habits" element={<HabitsPage />} />
  </Route>
</Route>
```

- If `isAuthenticated` is `false` → `<Navigate to="/login">` redirects the user
- If `isAuthenticated` is `true` → `<Outlet />` renders the child routes (PageLayout → DashboardPage)
- `replace` in `<Navigate>` means the redirect replaces the history entry — pressing Back won't loop back to the protected page

**`useAuthStore((s) => s.isAuthenticated)`** — Zustand selector. Only subscribes to `isAuthenticated`, not the entire store. If `user` changes but `isAuthenticated` doesn't, this component does NOT re-render.

---

## 3. `src/components/layout/PageLayout.tsx` — App Shell

### Type This Code:

```typescript
// Page layout — Navbar on top, Sidebar on left, content in the middle

import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

export default function PageLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

**Visual:**
```
┌──────────────────────────────────────────┐
│                Navbar                     │
├────────┬─────────────────────────────────┤
│        │                                  │
│Sidebar │      <Outlet />                  │
│        │  (DashboardPage, HabitsPage,     │
│        │   ChatPage, etc.)                │
│        │                                  │
└────────┴─────────────────────────────────┘
```

**`<Outlet />`** — React Router v6 concept. This is a placeholder that renders whatever child route is active. When the URL is `/habits`, Outlet renders `<HabitsPage />`. When it's `/analytics`, Outlet renders `<AnalyticsPage />`. The Navbar and Sidebar stay constant.

**`className="flex"`** — Tailwind flexbox. Sidebar and main sit side by side. `flex-1` on main makes it take all remaining horizontal space.

---

## 4. `src/components/layout/Navbar.tsx` — Top Bar

### Type This Code:

```typescript
// Top navigation bar — logo, user menu, logout

import { LogOut, User } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useNavigate } from "react-router-dom";

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <span className="text-2xl">🏥</span>
        <h1 className="text-xl font-bold text-brand-600">Health Tracker</h1>
      </div>

      {/* User menu */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <User className="w-4 h-4" />
          <span>{user?.full_name || "User"}</span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-red-600 transition-colors"
          aria-label="Logout"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
```

**`<User className="w-4 h-4" />`** — Lucide icons are React components. `w-4 h-4` is Tailwind for 16×16 pixels. Tree-shakable: only imported icons are included in the bundle.

**`user?.full_name`** — Optional chaining. If `user` is `null`, this evaluates to `undefined` instead of crashing. The `|| "User"` fallback handles that case.

---

## 5. `src/components/layout/Sidebar.tsx` — Side Navigation

### Type This Code:

```typescript
// Side navigation — links to all main pages

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ListChecks,
  CalendarCheck,
  BarChart3,
  MessageSquare,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/habits", icon: ListChecks, label: "Habits" },
  { to: "/check-in", icon: CalendarCheck, label: "Check In" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
  { to: "/chat", icon: MessageSquare, label: "AI Coach" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4">
      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

**`<NavLink>` vs `<Link>`** — `NavLink` knows if it matches the current URL. The `className` prop receives `{ isActive }` — we use it to highlight the current page. `<Link>` doesn't have this feature.

**`end={item.to === "/"}`** — Without `end`, the Dashboard link (`/`) would match ALL routes (because every URL starts with `/`). The `end` prop requires an **exact** match.

**`<item.icon className="w-5 h-5" />`** — Dynamic component rendering. `item.icon` is a React component (like `LayoutDashboard`). JSX allows rendering components stored in variables.

---

## 6. `src/components/layout/LoadingSpinner.tsx` — Reusable Spinner

### Type This Code:

```typescript
// Reusable loading spinner component

import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  text?: string;
}

export default function LoadingSpinner({
  className,
  size = "md",
  text,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  return (
    <div className={cn("flex flex-col items-center justify-center gap-2", className)}>
      <Loader2 className={cn("animate-spin text-brand-500", sizeClasses[size])} />
      {text && <p className="text-sm text-gray-500">{text}</p>}
    </div>
  );
}
```

**`animate-spin`** — Tailwind animation class. Rotates the icon continuously (CSS `animation: spin 1s linear infinite`).

**`size = "md"`** — Default parameter. If no `size` prop is passed, it defaults to `"md"`. The `sizeClasses` object maps size names to Tailwind width/height classes.

**`{text && <p>...`** — Short-circuit rendering. If `text` is `undefined` (prop not passed), the `<p>` tag doesn't render at all. This is how React does conditional rendering.

---

## 7. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **`cn()` utility** | utils.ts — Tailwind class merging (standard pattern) |
| 2 | **`<Outlet />`** | PageLayout — React Router renders child routes here |
| 3 | **Layout routes** | ProtectedRoute + PageLayout wrap all protected pages |
| 4 | **`<Navigate replace />`** | ProtectedRoute — redirect without history entry |
| 5 | **Zustand selector** | ProtectedRoute — subscribe to one field only |
| 6 | **`<NavLink>` with `isActive`** | Sidebar — highlight current page link |
| 7 | **`end` prop** | Sidebar — exact match for `/` route |
| 8 | **Dynamic component** | Sidebar — `<item.icon />` renders stored component |
| 9 | **Optional chaining `?.`** | Navbar — safe access on possibly null user |
| 10 | **Short-circuit rendering** | LoadingSpinner — `{text && <p>}` |

---

## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 16c: Store & Hooks](./phase4-part16c-frontend-store-hooks.md) |
| ➡️ Next | [Part 16e: Feature Components](./phase4-part16e-frontend-feature-components.md) |

---

**End of Phase 4 Part 16d: Layout Components & Utilities**
