import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
});

// Attach the JWT (stored in localStorage after login) to every request.
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("pm2dash_token");
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Redirect to /login on 401s - but NOT for the login request itself, otherwise
// a wrong password just hard-reloads the page instead of showing the error.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginRequest = err?.config?.url?.includes("/auth/login");
    if (typeof window !== "undefined" && err?.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem("pm2dash_token");
      localStorage.removeItem("pm2dash_role");
      localStorage.removeItem("pm2dash_username");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// ---- Types ----
export type Role = "admin" | "developer" | "viewer";

export interface ClientItem {
  id: number;
  name: string;
  description?: string | null;
  server_count: number;
  created_at: string;
}

export interface ServerItem {
  id: number;
  client_id: number;
  name: string;
  ip_address: string;
  ssh_port: number;
  ssh_username: string;
  pm2_path?: string | null;
  environment: "Dev" | "Prod" | "Stg" | "Other";
  tag?: string | null;
  online?: boolean | null;
}

export interface PM2ProcessItem {
  pm_id: number;
  name: string;
  pid?: number | null;
  status: string;
  cpu?: number | null;
  memory?: number | null;
  uptime?: number | null;
  restarts?: number | null;
  instances?: number | null;
  exec_mode?: string | null;
}
