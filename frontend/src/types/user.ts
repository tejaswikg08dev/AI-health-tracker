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
