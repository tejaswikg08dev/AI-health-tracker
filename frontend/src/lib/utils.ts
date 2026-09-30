// Utility functions used across the frontend

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * cn() — merge Tailwind CSS classes intelligently.
 *
 * Combines clsx (conditional classes) with tailwind-merge (dedup conflicting classes).
 * Example: cn("px-4 py-2", isActive && "bg-blue-500", "px-8")
 *   → "py-2 bg-blue-500 px-8" (px-4 is overridden by px-8)
 *
 * This is the standard utility in shadcn/ui and most Tailwind projects.
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
