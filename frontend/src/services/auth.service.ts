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
