"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Role } from "./api";

interface AuthState {
  username: string | null;
  role: Role | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ username: string; maskedEmail: string | null; otpRequired: boolean }>;
  verifyOtp: (username: string, code: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Auto-logout if the app was closed/inactive for this long, even
  // though the JWT itself might still technically be valid for longer.
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour

  function markActive() {
    localStorage.setItem("pm2dash_last_active", String(Date.now()));
  }

  useEffect(() => {
    const storedUser = localStorage.getItem("pm2dash_username");
    const storedRole = localStorage.getItem("pm2dash_role") as Role | null;
    const lastActiveRaw = localStorage.getItem("pm2dash_last_active");

    if (storedUser && storedRole) {
      const lastActive = lastActiveRaw ? Number(lastActiveRaw) : 0;
      const idleFor = Date.now() - lastActive;

      if (lastActiveRaw && idleFor > IDLE_TIMEOUT_MS) {
        // Was closed/inactive too long - require a fresh login, same as
        // a normal logout, but without redirecting (we're likely already
        // on /login or about to render the app shell).
        localStorage.removeItem("pm2dash_token");
        localStorage.removeItem("pm2dash_role");
        localStorage.removeItem("pm2dash_username");
        localStorage.removeItem("pm2dash_last_active");
      } else {
        setUsername(storedUser);
        setRole(storedRole);
        markActive();
      }
    }
    setIsLoading(false);
  }, []);

  // Keep the "last active" timestamp fresh while the app is actually open
  // and visible - minimizing/switching tabs briefly must NOT count as
  // being closed, only genuinely leaving it untouched for the full hour.
  useEffect(() => {
    if (!username) return;
    const interval = setInterval(markActive, 30 * 1000);
    function onVisibility() {
      if (document.visibilityState === "visible") markActive();
    }
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [username]);

  // Step 1: verifies username+password and triggers the emailed OTP.
  // Does NOT set auth state yet - that only happens after verifyOtp succeeds.
  async function login(usernameInput: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", usernameInput);
    form.append("password", password);
    const res = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { username: uname, masked_email, otp_required, access_token, role: userRole } = res.data;

    if (otp_required === false && access_token) {
      // Within the 1-hour grace period - the backend already issued a
      // real token, no OTP screen needed.
      localStorage.setItem("pm2dash_token", access_token);
      localStorage.setItem("pm2dash_role", userRole);
      localStorage.setItem("pm2dash_username", uname);
      markActive();
      setUsername(uname);
      setRole(userRole);
      router.push("/dashboard");
      return { username: uname, maskedEmail: null, otpRequired: false };
    }

    return { username: uname, maskedEmail: masked_email ?? null, otpRequired: true };
  }

  // Step 2: confirms the emailed code and completes sign-in.
  async function verifyOtp(usernameInput: string, code: string) {
    const res = await api.post("/auth/otp/verify", { username: usernameInput, code });
    const { access_token, role: userRole, username: uname } = res.data;
    localStorage.setItem("pm2dash_token", access_token);
    localStorage.setItem("pm2dash_role", userRole);
    localStorage.setItem("pm2dash_username", uname);
    markActive();
    setUsername(uname);
    setRole(userRole);
    router.push("/dashboard");
  }

  function logout() {
    localStorage.removeItem("pm2dash_token");
    localStorage.removeItem("pm2dash_role");
    localStorage.removeItem("pm2dash_username");
    localStorage.removeItem("pm2dash_last_active");
    setUsername(null);
    setRole(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ username, role, isLoading, login, verifyOtp, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("pm2dash_token");
}
