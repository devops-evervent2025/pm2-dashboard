"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import BuildLogTerminal from "@/components/BuildLogTerminal";

type ServerTarget = {
  server_id: number;
  server_name: string;
  process_name: string;
  status?: string;
  cwd: string;
  branch: string;
};

type BuildStatus = "connecting" | "open" | "closed" | "error";

type Job = {
  id: string;
  environment: string;
  repo: string;
  targets: ServerTarget[];
  minimized: boolean;
  startTimes: Record<string, number>;
  statuses: Record<string, BuildStatus>;
  erroredMap: Record<string, boolean>;
  expandedKeys: Set<string>;
};

async function authedGet(path: string) {
  const res = await api.get(path);
  return res.data;
}

function targetKey(t: ServerTarget) {
  return `${t.server_id}::${t.process_name}`;
}

function formatElapsed(startMs: number, _tick: number): string {
  const secs = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function statusBadge(status: BuildStatus, errored: boolean) {
  if (errored) return { label: "Failed", dot: "bg-red-500", pulse: false, text: "text-red-700 bg-red-50" };
  switch (status) {
    case "connecting":
      return { label: "Connecting", dot: "bg-amber-400", pulse: true, text: "text-amber-700 bg-amber-50" };
    case "open":
      return { label: "Running", dot: "bg-blue-500", pulse: true, text: "text-blue-700 bg-blue-50" };
    case "closed":
      return { label: "Done", dot: "bg-emerald-500", pulse: false, text: "text-emerald-700 bg-emerald-50" };
    case "error":
      return { label: "Error", dot: "bg-red-500", pulse: false, text: "text-red-700 bg-red-50" };
    default:
      return { label: "Connecting", dot: "bg-amber-400", pulse: true, text: "text-amber-700 bg-amber-50" };
  }
}

function jobAggregate(job: Job) {
  const total = job.targets.length;
  const doneCount = job.targets.filter((t) => {
    const s = job.statuses[targetKey(t)];
    return s === "closed" || s === "error";
  }).length;
  const anyError = job.targets.some((t) => job.erroredMap[targetKey(t)]);
  const allDone = total > 0 && doneCount === total;

  let badge;
  if (!allDone) badge = { label: "Running", dot: "bg-blue-500", pulse: true, text: "text-blue-700 bg-blue-50" };
  else if (anyError) badge = { label: "Done (errors)", dot: "bg-red-500", pulse: false, text: "text-red-700 bg-red-50" };
  else badge = { label: "Done", dot: "bg-emerald-500", pulse: false, text: "text-emerald-700 bg-emerald-50" };

  return { ...badge, doneCount, total, allDone };
}

export default function QuickDeployModal({ onClose }: { onClose: () => void }) {
  const { role } = useAuth();
  const canDeploy = role === "admin" || role === "developer";
  const [environments, setEnvironments] = useState<string[]>([]);
  const [environment, setEnvironment] = useState("");
  const [repos, setRepos] = useState<string[]>([]);
  const [repo, setRepo] = useState("");
  const [servers, setServers] = useState<ServerTarget[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<Job[]>([]);

  const [scanStatus, setScanStatus] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const loadEnvironments = () => {
    authedGet(`/build-manager/environments`)
      .then(setEnvironments)
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    loadEnvironments();
  }, []);

  const triggerScan = async () => {
    stopPolling();
    setScanning(true);
    setError(null);
    try {
      await api.post(`/build-manager/scan-deploy-targets`);
      pollRef.current = setInterval(async () => {
        try {
          const res = await api.get(`/build-manager/scan-deploy-targets/status`);
          setScanStatus(res.data);
          if (!res.data.running) {
            stopPolling();
            setScanning(false);
            loadEnvironments();
          }
        } catch {
          stopPolling();
          setScanning(false);
        }
      }, 3000);
    } catch (e: any) {
      setError(e?.response?.data?.detail || String(e));
      setScanning(false);
    }
  };

  useEffect(() => stopPolling, []);

  useEffect(() => {
    if (!environment) return;
    setLoading(true);
    setError(null);
    setRepo("");
    setServers([]);
    authedGet(`/build-manager/environments/${encodeURIComponent(environment)}/repos`)
      .then(setRepos)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [environment]);

  useEffect(() => {
    if (!environment || !repo) return;
    setLoading(true);
    setError(null);
    authedGet(
      `/build-manager/environments/${encodeURIComponent(environment)}/repos/${encodeURIComponent(repo)}/servers`
    )
      .then((rows: ServerTarget[]) => {
        setServers(rows);
        setSelectedKeys(rows.map(targetKey));
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [environment, repo]);

  const toggleKey = (key: string) => {
    setSelectedKeys((prev) => (prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key]));
  };

  const selectedTargets = servers.filter((s) => selectedKeys.includes(targetKey(s)));

  const [tick, setTick] = useState(0);
  const anyJobRunning = jobs.some((j) => !jobAggregate(j).allDone);
  useEffect(() => {
    if (!anyJobRunning) return;
    const interval = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, [anyJobRunning]);

  const startNewJob = () => {
    const now = Date.now();
    const startTimes: Record<string, number> = {};
    selectedTargets.forEach((t) => {
      startTimes[targetKey(t)] = now;
    });
    const firstKey = selectedTargets[0] ? targetKey(selectedTargets[0]) : null;

    const job: Job = {
      id: `${now}-${Math.random().toString(36).slice(2, 7)}`,
      environment,
      repo,
      targets: selectedTargets,
      minimized: false,
      startTimes,
      statuses: {},
      erroredMap: {},
      expandedKeys: new Set(firstKey ? [firstKey] : []),
    };

    setJobs((prev) => [job, ...prev]);
    setEnvironment("");
    setRepo("");
    setServers([]);
    setSelectedKeys([]);
  };

  const toggleJobMinimized = (jobId: string) => {
    setJobs((prev) => prev.map((j) => (j.id === jobId ? { ...j, minimized: !j.minimized } : j)));
  };

  const toggleTargetExpanded = (jobId: string, key: string) => {
    setJobs((prev) =>
      prev.map((j) => {
        if (j.id !== jobId) return j;
        const next = new Set(j.expandedKeys);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return { ...j, expandedKeys: next };
      })
    );
  };

  const updateJobTargetStatus = (jobId: string, key: string, status: BuildStatus, hadError: boolean) => {
    setJobs((prev) =>
      prev.map((j) => {
        if (j.id !== jobId) return j;
        return {
          ...j,
          statuses: { ...j.statuses, [key]: status },
          erroredMap: hadError ? { ...j.erroredMap, [key]: true } : j.erroredMap,
        };
      })
    );
  };

  const removeJob = (jobId: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
  };

  const handleClose = () => {
    if (anyJobRunning) {
      const ok = window.confirm(
        "Some builds are still running. Closing this window will stop watching their progress. Close anyway?"
      );
      if (!ok) return;
    }
    onClose();
  };

  const minimizedJobs = jobs.filter((j) => j.minimized);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-2xl lg:max-w-4xl xl:max-w-5xl max-h-[88vh] flex flex-col transition-all duration-300">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <h2 className="font-semibold text-slate-800 dark:text-slate-100">Quick Deploy</h2>
          <div className="flex items-center gap-3">
            {canDeploy && (
              <button
                onClick={triggerScan}
                disabled={scanning}
                className="text-xs px-2.5 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-50"
              >
                {scanning ? "Scanning…" : "Scan now"}
              </button>
            )}
            <button onClick={handleClose} className="text-slate-400 hover:text-slate-700">✕</button>
          </div>
        </div>

        {/* ---- scrollable middle: running/open jobs + the selection form ---- */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {error && <p className="text-sm text-red-600">{error}</p>}

          {jobs.map((job) => {
            const agg = jobAggregate(job);
            const earliestStart = Math.min(...Object.values(job.startTimes));
            return (
              <div
                key={job.id}
                style={{ display: job.minimized ? "none" : undefined }}
                className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
              >
                <div className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-slate-100 dark:bg-slate-800">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${agg.dot} ${agg.pulse ? "animate-pulse" : ""}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{job.repo}</p>
                      <p className="text-xs text-slate-500 truncate">
                        {job.environment} · {agg.doneCount}/{agg.total} server(s) done
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${agg.text}`}>{agg.label}</span>
                    <span className="text-xs text-slate-400 font-mono w-10 text-right">
                      {formatElapsed(earliestStart, tick)}
                    </span>
                    {agg.allDone && (
                      <button
                        onClick={() => removeJob(job.id)}
                        title="Dismiss"
                        className="text-slate-400 hover:text-slate-700 px-1"
                      >
                        ✕
                      </button>
                    )}
                    <button
                      onClick={() => toggleJobMinimized(job.id)}
                      title="Minimize"
                      className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500"
                    >
                      <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
                        <rect x="4" y="9" width="12" height="2" rx="1" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="p-3 space-y-2 bg-white dark:bg-slate-900">
                  {job.targets.map((t) => {
                    const key = targetKey(t);
                    const status = job.statuses[key] || "connecting";
                    const errored = job.erroredMap[key] || false;
                    const badge = statusBadge(status, errored);
                    const isExpanded = job.expandedKeys.has(key);
                    const startedAt = job.startTimes[key] || Date.now();

                    return (
                      <div key={key} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                        <button
                          type="button"
                          onClick={() => toggleTargetExpanded(job.id, key)}
                          className="w-full flex items-center justify-between gap-3 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-left"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${badge.dot} ${badge.pulse ? "animate-pulse" : ""}`} />
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">{t.server_name}</p>
                              <p className="text-xs text-slate-500 truncate font-mono">{t.process_name}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.text}`}>{badge.label}</span>
                            <span className="text-xs text-slate-400 font-mono w-10 text-right">{formatElapsed(startedAt, tick)}</span>
                            <svg
                              className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                              viewBox="0 0 20 20"
                              fill="currentColor"
                            >
                              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                            </svg>
                          </div>
                        </button>
                        <div
                          className="transition-all duration-300 ease-in-out overflow-hidden"
                          style={{ maxHeight: isExpanded ? "75vh" : "0px" }}
                        >
                          <div className="p-3">
                            <BuildLogTerminal
                              title={`${t.server_name} · ${t.process_name}`}
                              wsPath={`/build-manager/ws-by-process/${t.server_id}/${encodeURIComponent(t.process_name)}`}
                              onStatusChange={(s, hadError) => updateJobTargetStatus(job.id, key, s, hadError)}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* ---- selection form: always visible, so a new deploy can be queued anytime ---- */}
          {canDeploy && (
          <div className="space-y-4 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">New Deploy</p>

            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">1. Environment</label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
              >
                <option value="">Select environment…</option>
                {environments.map((env) => (
                  <option key={env} value={env}>{env}</option>
                ))}
              </select>
              {environment && (
                <p className="text-xs text-slate-500 mt-1">
                  Branch auto-mapped to: <code>{environment}</code>
                </p>
              )}
            </div>

            {environment && (
              <div>
                <label className="text-sm font-medium text-slate-700 dark:text-slate-200">2. Repository</label>
                <select
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  disabled={loading || repos.length === 0}
                  className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm dark:bg-slate-800 dark:border-slate-600"
                >
                  <option value="">{loading ? "Loading…" : "Select repository…"}</option>
                  {repos.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                {!loading && repos.length === 0 && (
                  <p className="text-xs text-slate-500 mt-1">
                    No repos found yet for this environment — hit "Scan now" above.
                  </p>
                )}
              </div>
            )}

            {repo && (
              <div>
                <label className="text-sm font-medium text-slate-700 dark:text-slate-200">3. PM2 processes</label>
                {loading ? (
                  <p className="text-xs text-slate-500 mt-1">Loading…</p>
                ) : servers.length === 0 ? (
                  <p className="text-xs text-slate-500 mt-1">No cached pm2 process found for this repo.</p>
                ) : (
                  <div className="mt-1 space-y-1.5">
                    {servers.map((s) => (
                      <label key={targetKey(s)} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={selectedKeys.includes(targetKey(s))}
                          onChange={() => toggleKey(targetKey(s))}
                        />
                        {s.server_name}
                        <span className="text-xs font-mono text-slate-500">{s.process_name}</span>
                        <span className="text-xs text-slate-400">{s.cwd}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}

            {selectedTargets.length > 0 && (
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                <p className="text-xs text-slate-500 mb-3">
                  Will run <code>npm i -f &amp;&amp; npm run build</code> then restart {selectedTargets.length} pm2 process(es) by exact name.
                </p>
                <button
                  onClick={startNewJob}
                  className="w-full bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg py-2.5"
                >
                  Run Build &amp; Restart
                </button>
              </div>
            )}
          </div>
          )}

          {!canDeploy && jobs.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-6">
              You have view-only access. Ask an admin or developer to run a deploy.
            </p>
          )}
        </div>

        {/* ---- taskbar: minimized job pills, Windows-style ---- */}
        {minimizedJobs.length > 0 && (
          <div className="shrink-0 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 flex items-center gap-2 overflow-x-auto">
            {minimizedJobs.map((job) => {
              const agg = jobAggregate(job);
              return (
                <button
                  key={job.id}
                  onClick={() => toggleJobMinimized(job.id)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 hover:border-brand-400 hover:shadow-sm transition-all shrink-0"
                  title={`${job.repo} · ${job.environment} — click to restore`}
                >
                  <span className={`w-2 h-2 rounded-full ${agg.dot} ${agg.pulse ? "animate-pulse" : ""}`} />
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-200 max-w-[10rem] truncate">
                    {job.repo}
                  </span>
                  <span className="text-[10px] text-slate-400">{agg.doneCount}/{agg.total}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
