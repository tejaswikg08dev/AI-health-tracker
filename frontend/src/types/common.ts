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
