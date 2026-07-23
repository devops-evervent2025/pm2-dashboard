"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Role } from "./api";

interface AuthState {
  username: string | null;
  role: Role | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const storedUser = localStorage.getItem("pm2dash_username");
    const storedRole = localStorage.getItem("pm2dash_role") as Role | null;
    if (storedUser && storedRole) {
      setUsername(storedUser);
      setRole(storedRole);
    }
    setIsLoading(false);
  }, []);

  async function login(usernameInput: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", usernameInput);
    form.append("password", password);
    const res = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { access_token, role: userRole, username: uname } = res.data;
    localStorage.setItem("pm2dash_token", access_token);
    localStorage.setItem("pm2dash_role", userRole);
    localStorage.setItem("pm2dash_username", uname);
    setUsername(uname);
    setRole(userRole);
    router.push("/dashboard");
  }

  function logout() {
    localStorage.removeItem("pm2dash_token");
    localStorage.removeItem("pm2dash_role");
    localStorage.removeItem("pm2dash_username");
    setUsername(null);
    setRole(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ username, role, isLoading, login, logout }}>
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
