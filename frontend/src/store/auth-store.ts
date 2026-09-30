// ============================================================================
// Auth Store — Zustand (Global State Management)
// ============================================================================
// WHAT THIS FILE DOES:
//   Manages authentication state globally: user, tokens, isAuthenticated.
//   Persisted to localStorage so the user stays logged in on page refresh.
//
// WHY ZUSTAND (not Redux, not Context):
//   - Zustand: 1KB, zero boilerplate, works outside React (interceptors)
//   - Redux: 10KB+, tons of boilerplate, overkill for a personal app
//   - Context: causes unnecessary re-renders, can't use outside React
//
//   Zustand is the sweet spot for small-to-medium apps.
//   Companies use Redux for very large apps (100+ global state fields).
//
// USAGE:
//   const { user, login, logout } = useAuthStore();
//   await login(email, password); // Sets user + tokens + localStorage
//   logout();                     // Clears everything
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
