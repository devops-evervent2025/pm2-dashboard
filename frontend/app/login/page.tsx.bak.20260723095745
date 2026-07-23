"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lockedSeconds, setLockedSeconds] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (lockedSeconds === null) return;
    if (lockedSeconds <= 0) {
      setLockedSeconds(null);
      setError(null);
      return;
    }
    intervalRef.current = setInterval(() => {
      setLockedSeconds((prev) => (prev !== null ? prev - 1 : null));
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lockedSeconds]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail && typeof detail === "object" && "retry_after_seconds" in detail) {
        setLockedSeconds(detail.retry_after_seconds);
        setError(detail.message || "Account locked due to too many failed attempts.");
      } else {
        setError(typeof detail === "string" ? detail : "Login failed");
      }
    } finally {
      setLoading(false);
    }
  }

  const isLocked = lockedSeconds !== null && lockedSeconds > 0;

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card w-full max-w-sm p-8">
        <h1 className="text-xl font-semibold mb-1">PM2 Dashboard</h1>
        <p className="text-sm text-slate-500 mb-6">Sign in to manage your clients & servers</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              className="input-field"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={isLocked}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              className="input-field"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLocked}
            />
          </div>
          {error && (
            <div className="text-sm text-red-600">
              <p>{error}</p>
              {isLocked && (
                <p className="mt-1 font-medium">
                  Try again in {formatCountdown(lockedSeconds as number)}
                </p>
              )}
            </div>
          )}
          <button type="submit" disabled={loading || isLocked} className="btn-primary w-full">
            {isLocked
              ? `Locked - ${formatCountdown(lockedSeconds as number)}`
              : loading
              ? "Signing in…"
              : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
