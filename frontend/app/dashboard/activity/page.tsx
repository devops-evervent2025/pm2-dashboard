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
  role?: string | null;
  client_name?: string | null;
  environment?: string | null;
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

const ENV_STYLES: Record<string, string> = {
  Dev: "bg-blue-50 text-blue-600",
  Prod: "bg-red-50 text-red-600",
  Stg: "bg-amber-50 text-amber-600",
  Other: "bg-slate-100 text-slate-500",
};

export default function ActivityLogPage() {
  const { role: myRole, isLoading } = useAuth();
  const router = useRouter();

  const [entries, setEntries] = useState<ActivityLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const [usernameQuery, setUsernameQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [clientQuery, setClientQuery] = useState("");
  const [envFilter, setEnvFilter] = useState("");

  const fetchLog = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit: 300 };
      if (usernameQuery.trim()) params.username = usernameQuery.trim();
      if (roleFilter) params.role = roleFilter;
      if (clientQuery.trim()) params.client = clientQuery.trim();
      if (envFilter) params.environment = envFilter;

      const res = await api.get<ActivityLogEntry[]>("/activity-log", { params });
      setEntries(res.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load activity log");
    } finally {
      setLoading(false);
    }
  }, [usernameQuery, roleFilter, clientQuery, envFilter]);

  useEffect(() => {
    if (!isLoading && !myRole) {
      router.replace("/login");
      return;
    }
    if (!isLoading && myRole && myRole !== "admin") {
      router.replace("/dashboard");
      return;
    }
    if (myRole === "admin") fetchLog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myRole, isLoading, router]);

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    fetchLog();
  }

  function clearFilters() {
    setUsernameQuery("");
    setRoleFilter("");
    setClientQuery("");
    setEnvFilter("");
  }

  if (myRole && myRole !== "admin") return null;

  const visible = typeFilter === "all" ? entries : entries.filter((e) => e.type === typeFilter);

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "Activity Log" }]} />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Activity Log</h1>
            <p className="text-sm text-slate-500">
              Who revealed which secrets, ran which curl commands, and viewed which process logs.
              Entries older than 7 days are automatically removed.
            </p>
          </div>
          <button className="btn-secondary text-sm" onClick={fetchLog} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        <form onSubmit={handleSearchSubmit} className="card p-4 mb-4">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">User name</label>
              <input
                className="input-field text-sm"
                placeholder="e.g. anjali"
                value={usernameQuery}
                onChange={(e) => setUsernameQuery(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Role</label>
              <select
                className="input-field text-sm"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
              >
                <option value="">Any role</option>
                <option value="admin">admin</option>
                <option value="developer">developer</option>
                <option value="viewer">viewer</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Client</label>
              <input
                className="input-field text-sm"
                placeholder="e.g. Amaze"
                value={clientQuery}
                onChange={(e) => setClientQuery(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Environment</label>
              <select
                className="input-field text-sm"
                value={envFilter}
                onChange={(e) => setEnvFilter(e.target.value)}
              >
                <option value="">Any environment</option>
                <option value="Dev">Dev</option>
                <option value="Stg">Stg</option>
                <option value="Prod">Prod</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <button type="button" onClick={clearFilters} className="btn-secondary text-xs">
              Clear
            </button>
            <button type="submit" className="btn-primary text-xs">
              Search
            </button>
          </div>
        </form>

        <div className="flex gap-2 mb-4">
          {["all", "secret_reveal", "curl_command", "log_view"].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                typeFilter === t
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
          <div className="card p-10 text-center text-slate-500">
            No activity found for these filters.
          </div>
        )}

        <div className="card divide-y divide-slate-100 overflow-hidden">
          {visible.map((e) => (
            <div key={e.id} className="px-4 py-3 flex items-start justify-between gap-4 text-sm">
              <div className="min-w-0">
                <p className="text-slate-800">{e.detail}</p>
                <p className="text-xs text-slate-400 mt-0.5 flex flex-wrap items-center gap-1.5">
                  <span>{e.username || "unknown user"}</span>
                  {e.role && <span className="badge bg-slate-100 text-slate-500">{e.role}</span>}
                  {e.client_name && <span>· {e.client_name}</span>}
                  {e.environment && (
                    <span className={`badge ${ENV_STYLES[e.environment] || ENV_STYLES.Other}`}>
                      {e.environment}
                    </span>
                  )}
                  <span>· {new Date(e.timestamp).toLocaleString()}</span>
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
