"use client";

import { useCallback, useEffect, useState } from "react";
import { api, EnvFileItem } from "@/lib/api";
import { LoadingState } from "@/components/Preloader";

export interface UnifiedRepo {
  key: string;
  name: string;
  source: "local" | { scanPathId: number; serverName: string; basePath: string; label?: string | null };
}

function envUrlFor(repo: UnifiedRepo, suffix: string): string {
  if (repo.source === "local") {
    return `/system/repos/${encodeURIComponent(repo.name)}/env${suffix}`;
  }
  return `/remote-repos/scan-paths/${repo.source.scanPathId}/repos/${encodeURIComponent(
    repo.name
  )}/env${suffix}`;
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
      <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
    </svg>
  );
}

function ScanIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path
        fillRule="evenodd"
        d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.389zm1.585-8.885a.75.75 0 00-1.449.389 5.5 5.5 0 019.62 3.045h-2.433a.75.75 0 000 1.5h4.243a.75.75 0 00.75-.75V1.756a.75.75 0 00-1.5 0v2.43l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.5 2.55l.397-.01z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function EnvRepoGroupModal({
  groupLabel,
  repos,
  onClose,
  onScanComplete,
}: {
  groupLabel: string;
  repos: UnifiedRepo[];
  onClose: () => void;
  onScanComplete?: (scanPathId: number, repoNames: string[]) => void;
}) {
  const [selectedRepo, setSelectedRepo] = useState<UnifiedRepo | null>(null);
  const [envFiles, setEnvFiles] = useState<EnvFileItem[]>([]);
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [loadingEnv, setLoadingEnv] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [copying, setCopying] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scanPathId = repos[0]?.source !== "local" ? repos[0]?.source.scanPathId : null;
  const isLocal = repos[0]?.source === "local";

  const loadEnv = useCallback(async (repo: UnifiedRepo) => {
    setSelectedRepo(repo);
    setEnvFiles([]);
    setRevealed({});
    setLoadingEnv(true);
    setError(null);
    try {
      const res = await api.get<EnvFileItem[]>(envUrlFor(repo, ""));
      setEnvFiles(res.data);

      const revealTasks: Promise<void>[] = [];
      for (const file of res.data) {
        for (const k of file.keys) {
          if (!k.is_sensitive) continue;
          const mapKey = `${file.file_path}::${k.key}`;
          revealTasks.push(
            api
              .post(envUrlFor(repo, "/reveal"), { file_path: file.file_path, key: k.key })
              .then((r) => {
                setRevealed((prev) => ({ ...prev, [mapKey]: r.data.value }));
              })
              .catch(() => {
                setRevealed((prev) => ({ ...prev, [mapKey]: "(could not reveal)" }));
              })
          );
        }
      }
      await Promise.all(revealTasks);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load .env files for this repo");
    } finally {
      setLoadingEnv(false);
    }
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  function fileAsText(file: EnvFileItem): string {
    return file.keys
      .map((k) => {
        const mapKey = `${file.file_path}::${k.key}`;
        const value = k.is_sensitive ? revealed[mapKey] ?? "••••••••" : k.value ?? "";
        return `${k.key}=${value}`;
      })
      .join("\n");
  }

  function allEnvAsText(): string {
    return envFiles
      .map((file) => `# ${selectedRepo?.name}/${file.file_path}\n${fileAsText(file)}`)
      .join("\n\n");
  }

  async function handleCopy() {
    if (!selectedRepo || envFiles.length === 0) return;
    setCopying(true);
    try {
      await navigator.clipboard.writeText(allEnvAsText());
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      alert("Could not copy - your browser may be blocking clipboard access.");
    } finally {
      setCopying(false);
    }
  }

  async function handleScan() {
    setScanning(true);
    setError(null);
    try {
      if (scanPathId != null) {
        const res = await api.post<{
          scan_path_id: number;
          repos_found: number;
          repo_names: string[];
        }>(`/remote-repos/scan-paths/${scanPathId}/scan`);
        onScanComplete?.(res.data.scan_path_id, res.data.repo_names);
      }
      if (selectedRepo) {
        await loadEnv(selectedRepo);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  const canCopy = !!selectedRepo && !loadingEnv && envFiles.length > 0;
  const canScan = !scanning && (isLocal ? !!selectedRepo : scanPathId != null);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm dark:bg-slate-950/70" />

      <div
        className="relative flex max-h-[min(88vh,860px)] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700/80 dark:bg-slate-900 dark:shadow-black/40"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 bg-slate-50 px-5 py-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="min-w-0">
            <p className="mb-1 text-[11px] uppercase tracking-wider text-slate-500">Environment group</p>
            <h2 className="truncate text-lg font-semibold text-slate-800 dark:text-slate-100">{groupLabel}</h2>
            {selectedRepo && (
              <p className="mt-1 truncate text-sm text-slate-500 dark:text-slate-400">
                Viewing <span className="font-mono text-brand-600 dark:text-sky-300">{selectedRepo.name}</span>
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={handleScan}
              disabled={!canScan}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300 dark:hover:bg-emerald-500/20"
              title={isLocal ? "Refresh .env from disk" : "Re-scan this server path"}
            >
              <ScanIcon />
              {scanning ? "Scanning…" : "Scan"}
            </button>
            <button
              type="button"
              onClick={handleCopy}
              disabled={!canCopy || copying}
              className="inline-flex items-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700 transition-colors hover:bg-brand-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-300 dark:hover:bg-sky-500/20"
            >
              <CopyIcon />
              {copied ? "Copied!" : "Copy"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary inline-flex items-center gap-1.5 px-3 py-1.5 text-xs"
            >
              <CloseIcon />
              Close
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-white dark:bg-slate-900">
          {!selectedRepo ? (
            <div className="p-2">
              <p className="px-3 py-2 text-xs text-slate-500">Select a repository to view its .env files.</p>
              <div className="overflow-hidden rounded-xl border border-slate-200 divide-y divide-slate-200 dark:border-slate-800 dark:divide-slate-800">
                {repos.map((repo) => (
                  <button
                    key={repo.key}
                    type="button"
                    onClick={() => loadEnv(repo)}
                    className="group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/70"
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-500 transition-colors group-hover:border-brand-300 group-hover:text-brand-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:group-hover:border-sky-500/40 dark:group-hover:text-sky-300">
                      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                        <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                      </svg>
                    </span>
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{repo.name}</span>
                    <span className="ml-auto text-xs text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-400">
                      Open
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 p-4">
              <button
                type="button"
                onClick={() => {
                  setSelectedRepo(null);
                  setEnvFiles([]);
                  setRevealed({});
                  setError(null);
                }}
                className="text-xs text-brand-600 hover:text-brand-700 dark:text-sky-400 dark:hover:text-sky-300"
              >
                ← Back to repos
              </button>

              {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

              {loadingEnv && (
                <LoadingState message={`Loading .env files for ${selectedRepo.name}`} variant="compact" />
              )}

              {!loadingEnv && envFiles.length === 0 && !error && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-950/50">
                  No .env files found (checked .env, backend/.env, frontend/.env).
                </div>
              )}

              {!loadingEnv &&
                envFiles.map((file) => (
                  <div
                    key={file.file_path}
                    className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800"
                  >
                    <div className="border-b border-slate-200 bg-slate-50 px-4 py-2.5 dark:border-slate-800 dark:bg-slate-900/80">
                      <span className="text-xs font-mono text-slate-600 dark:text-slate-300">
                        {selectedRepo.name}/{file.file_path}
                      </span>
                    </div>
                    <div className="overflow-x-auto bg-slate-900 p-4 font-mono text-xs">
                      {file.keys.map((k) => {
                        const mapKey = `${file.file_path}::${k.key}`;
                        const value = k.is_sensitive ? revealed[mapKey] : k.value;
                        return (
                          <div key={k.key} className="flex items-center gap-2 whitespace-pre py-0.5">
                            <span className="text-sky-400">{k.key}</span>
                            <span className="text-slate-600">=</span>
                            <span className={k.is_sensitive ? "text-amber-300" : "text-emerald-300"}>
                              {value || <span className="italic text-slate-600">(empty)</span>}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
