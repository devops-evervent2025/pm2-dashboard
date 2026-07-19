"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

interface ActivityLogEntry {
  id: string;
  type: "secret_reveal" | "curl_command" | "log_view";
  timestamp: string;
  username?: string | null;
  detail: string;
}

const TYPE_STYLES: Record<string, string> = {
  secret_reveal: "bg-red-100 text-red-700",
  curl_command: "bg-blue-100 text-blue-700",
  log_view: "bg-slate-100 text-slate-600",
};

const TYPE_LABELS: Record<string, string> = {
  secret_reveal: "Secret Reveal",
  curl_command: "Curl Command",
  log_view: "Log View",
};

export default function ActivityLogPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [entries, setEntries] = useState<ActivityLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");

  const fetchLog = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<ActivityLogEntry[]>("/activity-log", { params: { limit: 300 } });
      setEntries(res.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load activity log");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (!isLoading && role && role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    if (role === "admin") fetchLog();
  }, [role, isLoading, router, fetchLog]);

  if (role && role !== "admin") return null;

  const visible = filterType === "all" ? entries : entries.filter((e) => e.type === filterType);

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "Activity Log" }]} />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Activity Log</h1>
            <p className="text-sm text-slate-500">
              Who revealed which secrets, ran which curl commands, and viewed which process logs.
            </p>
          </div>
          <button className="btn-secondary text-sm" onClick={fetchLog} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        <div className="flex gap-2 mb-4">
          {["all", "secret_reveal", "curl_command", "log_view"].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterType === t
                  ? "bg-brand-50 text-brand-700"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {t === "all" ? "All" : TYPE_LABELS[t]}
            </button>
          ))}
        </div>

        {error && <p className="text-red-600 mb-4">{error}</p>}
        {loading && entries.length === 0 && <p className="text-slate-500">Loading…</p>}

        {!loading && visible.length === 0 && !error && (
          <div className="card p-10 text-center text-slate-500">No activity recorded yet.</div>
        )}

        <div className="card divide-y divide-slate-100 overflow-hidden">
          {visible.map((e) => (
            <div key={e.id} className="px-4 py-3 flex items-start justify-between gap-4 text-sm">
              <div className="min-w-0">
                <p className="text-slate-800">{e.detail}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {e.username || "unknown user"} · {new Date(e.timestamp).toLocaleString()}
                </p>
              </div>
              <span className={`badge shrink-0 ${TYPE_STYLES[e.type]}`}>{TYPE_LABELS[e.type]}</span>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
