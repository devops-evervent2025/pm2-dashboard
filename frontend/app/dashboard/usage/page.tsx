"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

interface ActivityStatsDay {
  date: string;
  counts: Record<string, number>;
  total: number;
}

interface ActivityStatsUser {
  username: string;
  role: string;
  counts: Record<string, number>;
  total: number;
}

interface ActivityStatsResponse {
  days: number;
  username_filter?: string | null;
  viewing_as_admin: boolean;
  total_actions: number;
  totals_by_type: Record<string, number>;
  timeline: ActivityStatsDay[];
  by_user: ActivityStatsUser[];
  available_users: string[];
}

const ACTIVITY_TYPE_ORDER = ["log_view", "curl_command", "env_edit", "build_run", "secret_reveal"] as const;

const TYPE_META: Record<string, { label: string; color: string; bg: string; short: string }> = {
  log_view: { label: "Log views", color: "#64748b", bg: "bg-slate-500", short: "Logs" },
  curl_command: { label: "Terminal commands", color: "#3b82f6", bg: "bg-blue-500", short: "Terminal" },
  env_edit: { label: "Env edits", color: "#8b5cf6", bg: "bg-violet-500", short: "Env edit" },
  build_run: { label: "Build / deploy", color: "#f59e0b", bg: "bg-amber-500", short: "Build" },
  secret_reveal: { label: "Secret reveals", color: "#ef4444", bg: "bg-red-500", short: "Secrets" },
};

const MAX_X_LABELS = 5;

function formatDayLabel(dateStr: string, compact = false): string {
  const d = new Date(`${dateStr}T00:00:00`);
  if (compact) {
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function TimelineChart({ timeline }: { timeline: ActivityStatsDay[] }) {
  const rawMax = Math.max(0, ...timeline.map((d) => d.total));
  const maxTotal = rawMax === 0 ? 1 : rawMax;
  const labelStep =
    timeline.length <= MAX_X_LABELS ? 1 : Math.max(1, Math.ceil(timeline.length / MAX_X_LABELS));
  const compactLabels = timeline.length > MAX_X_LABELS;

  const barGap = timeline.length > 14 ? 4 : 6;
  const barW = timeline.length > 20 ? 14 : timeline.length > 14 ? 18 : timeline.length > 7 ? 22 : 28;

  const chartH = 260;
  const pad = { top: 16, right: 16, bottom: 36, left: 32 };
  const innerH = chartH - pad.top - pad.bottom;
  const chartW = Math.max(680, pad.left + pad.right + timeline.length * (barW + barGap) - barGap);

  const yTicks =
    rawMax === 0
      ? [0]
      : Array.from(new Set([0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(maxTotal * t)))).sort(
          (a, b) => a - b
        );

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-100 dark:border-slate-800">
      <svg viewBox={`0 0 ${chartW} ${chartH}`} className="h-auto min-w-full" style={{ minWidth: chartW }}>
        {yTicks.map((val) => {
          const t = maxTotal === 0 ? 0 : val / maxTotal;
          const y = pad.top + innerH * (1 - t);
          return (
            <g key={val}>
              <line
                x1={pad.left}
                y1={y}
                x2={chartW - pad.right}
                y2={y}
                stroke="currentColor"
                className="text-slate-200 dark:text-slate-700"
                strokeDasharray="4 4"
              />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" className="fill-slate-400 text-[10px]">
                {val}
              </text>
            </g>
          );
        })}

        {timeline.map((day, i) => {
          const x = pad.left + i * (barW + barGap);
          let yCursor = pad.top + innerH;
          const segments = ACTIVITY_TYPE_ORDER.map((key) => ({
            key,
            value: day.counts[key] || 0,
          }));
          const showLabel = i % labelStep === 0 || i === timeline.length - 1;

          return (
            <g key={day.date}>
              {segments.map((seg) => {
                if (!seg.value) return null;
                const h = (seg.value / maxTotal) * innerH;
                yCursor -= h;
                return (
                  <rect
                    key={seg.key}
                    x={x}
                    y={yCursor}
                    width={barW}
                    height={Math.max(h, 2)}
                    rx={2}
                    fill={TYPE_META[seg.key]?.color || "#94a3b8"}
                    className="opacity-90 hover:opacity-100"
                  >
                    <title>{`${formatDayLabel(day.date, true)} — ${TYPE_META[seg.key]?.label}: ${seg.value}`}</title>
                  </rect>
                );
              })}
              {showLabel && (
                <text
                  x={x + barW / 2}
                  y={chartH - 10}
                  textAnchor="middle"
                  className="fill-slate-500 text-[10px]"
                >
                  {formatDayLabel(day.date, true)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function TypeDonut({ totals }: { totals: Record<string, number> }) {
  const entries = ACTIVITY_TYPE_ORDER.map((key) => ({
    key,
    ...TYPE_META[key],
    value: totals[key] || 0,
  }));
  const total = entries.reduce((s, e) => s + e.value, 0);
  const r = 54;
  const cx = 70;
  const cy = 70;
  let angle = -Math.PI / 2;
  const sliceTotal = total || 1;

  const slices = entries.map((e) => {
    const slice = (e.value / sliceTotal) * Math.PI * 2;
    const x1 = cx + r * Math.cos(angle);
    const y1 = cy + r * Math.sin(angle);
    angle += slice;
    const x2 = cx + r * Math.cos(angle);
    const y2 = cy + r * Math.sin(angle);
    const large = slice > Math.PI ? 1 : 0;
    const path = e.value
      ? `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
      : "";
    return { ...e, path };
  });

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:justify-center">
      <svg viewBox="0 0 140 140" className="h-36 w-36 shrink-0">
        {total > 0 &&
          slices.map((s) =>
            s.path ? <path key={s.key} d={s.path} fill={s.color} opacity={0.9} /> : null
          )}
        <circle cx={cx} cy={cy} r={total > 0 ? 34 : 54} className="fill-slate-100 stroke-slate-200 dark:fill-slate-800 dark:stroke-slate-700" strokeWidth={total > 0 ? 0 : 1} />
        {total > 0 && <circle cx={cx} cy={cy} r={34} className="fill-white dark:fill-slate-900" />}
        <text x={cx} y={cy - 2} textAnchor="middle" className="fill-slate-800 dark:fill-slate-100 text-[18px] font-semibold">
          {total}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" className="fill-slate-500 text-[9px]">
          actions
        </text>
      </svg>
      <div className="space-y-2">
        {entries.map((e) => (
          <div key={e.key} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: e.color }} />
            <span className="text-slate-600 dark:text-slate-300">{e.label}</span>
            <span className="ml-auto font-medium text-slate-800 dark:text-slate-100">{e.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function UserBarChart({ users }: { users: ActivityStatsUser[] }) {
  const top = users.slice(0, 10);
  const max = Math.max(1, ...top.map((u) => u.total));

  return (
    <div className="space-y-3">
      {top.map((u) => (
        <div key={u.username}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {u.username}
              <span className="ml-2 text-slate-400">({u.role})</span>
            </span>
            <span className="text-slate-500">{u.total}</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className="flex h-full overflow-hidden rounded-full"
              style={{ width: `${(u.total / max) * 100}%` }}
            >
              {ACTIVITY_TYPE_ORDER.map((key) => {
                const val = u.counts[key] || 0;
                if (!val) return null;
                return (
                  <div
                    key={key}
                    style={{
                      width: `${(val / u.total) * 100}%`,
                      backgroundColor: TYPE_META[key]?.color,
                    }}
                  />
                );
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function UserActivityPage() {
  const { role, username, isLoading } = useAuth();
  const router = useRouter();
  const [days, setDays] = useState(7);
  const [userFilter, setUserFilter] = useState("");
  const [stats, setStats] = useState<ActivityStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = role === "admin";

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { days };
      if (isAdmin && userFilter) params.username = userFilter;
      const res = await api.get<ActivityStatsResponse>("/activity-log/stats", { params });
      setStats(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load activity stats");
    } finally {
      setLoading(false);
    }
  }, [days, userFilter, isAdmin]);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchStats();
  }, [role, isLoading, router, fetchStats]);

  const title = useMemo(() => {
    if (isAdmin && userFilter) return `Activity for ${userFilter}`;
    if (isAdmin) return "All users activity";
    return `My activity (${username || "you"})`;
  }, [isAdmin, userFilter, username]);

  if (!role) return null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Navbar crumbs={[{ label: "User Activity" }]} />
      <div className="flex-1 overflow-y-auto min-h-0">
        <main className="w-full px-4 py-6 lg:px-6">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-800 dark:text-slate-100">User Activity</h1>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {isAdmin
                  ? "Track dashboard usage across five action types — logs, terminal, env edits, builds, and secret reveals."
                  : "Your personal usage across five action types over the selected period."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                className="input-field text-sm w-auto min-w-[120px]"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
              </select>

              {isAdmin && (
                <select
                  className="input-field text-sm w-auto min-w-[160px]"
                  value={userFilter}
                  onChange={(e) => setUserFilter(e.target.value)}
                >
                  <option value="">All users</option>
                  {(stats?.available_users || []).map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              )}

              <button className="btn-secondary text-sm" onClick={fetchStats} disabled={loading}>
                {loading ? "Loading…" : "Refresh"}
              </button>
            </div>
          </div>

          {error && <p className="mb-4 text-red-600 dark:text-red-400">{error}</p>}

          {loading && !stats && <p className="text-sm text-slate-500">Loading charts…</p>}

          {stats && (
            <>
              <p className="mb-4 text-sm font-medium text-slate-600 dark:text-slate-300">{title}</p>

              <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
                <div className="card p-4">
                  <p className="text-xs uppercase tracking-wider text-slate-500">Total actions</p>
                  <p className="mt-1 text-2xl font-semibold text-slate-800 dark:text-slate-100">{stats.total_actions}</p>
                </div>
                {ACTIVITY_TYPE_ORDER.map((key) => {
                  const meta = TYPE_META[key];
                  return (
                    <div key={key} className="card p-4">
                      <p className="truncate text-xs uppercase tracking-wider text-slate-500">{meta.short}</p>
                      <p className="mt-1 text-2xl font-semibold text-slate-800 dark:text-slate-100">
                        {stats.totals_by_type[key] || 0}
                      </p>
                    </div>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <div className="card p-5 xl:col-span-2">
                  <h2 className="mb-1 text-sm font-semibold text-slate-800 dark:text-slate-100">Daily activity</h2>
                  <p className="mb-4 text-xs text-slate-500">Stacked by action type</p>
                  <TimelineChart timeline={stats.timeline} />
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500 sm:grid-cols-3 lg:grid-cols-5">
                    {ACTIVITY_TYPE_ORDER.map((key) => {
                      const meta = TYPE_META[key];
                      return (
                        <span key={key} className="inline-flex items-center gap-1.5">
                          <span className={`h-2 w-2 shrink-0 rounded-full ${meta.bg}`} />
                          <span className="truncate">{meta.label}</span>
                        </span>
                      );
                    })}
                  </div>
                </div>

                <div className="card p-5">
                  <h2 className="mb-1 text-sm font-semibold text-slate-800 dark:text-slate-100">Breakdown</h2>
                  <p className="mb-4 text-xs text-slate-500">Share by action type</p>
                  <TypeDonut totals={stats.totals_by_type} />
                </div>
              </div>

              {isAdmin && !userFilter && stats.by_user.length > 0 && (
                <div className="card mt-6 p-5">
                  <h2 className="mb-1 text-sm font-semibold text-slate-800 dark:text-slate-100">Top users</h2>
                  <p className="mb-4 text-xs text-slate-500">Who is using the dashboard most</p>
                  <UserBarChart users={stats.by_user} />
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
