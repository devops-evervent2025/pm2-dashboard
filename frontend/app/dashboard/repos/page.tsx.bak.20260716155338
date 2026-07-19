"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, RepoItem, EnvFileItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

export default function ReposPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [repos, setRepos] = useState<RepoItem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [envFiles, setEnvFiles] = useState<EnvFileItem[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingEnv, setLoadingEnv] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [revealing, setRevealing] = useState<string | null>(null);

  const fetchRepos = useCallback(async () => {
    setLoadingRepos(true);
    try {
      const res = await api.get<RepoItem[]>("/system/repos");
      setRepos(res.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load repos");
    } finally {
      setLoadingRepos(false);
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
    if (role === "admin") fetchRepos();
  }, [role, isLoading, router, fetchRepos]);

  async function openRepo(name: string) {
    setSelectedRepo(name);
    setEnvFiles([]);
    setRevealed({});
    setLoadingEnv(true);
    try {
      const res = await api.get<EnvFileItem[]>(`/system/repos/${encodeURIComponent(name)}/env`);
      setEnvFiles(res.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load .env files for this repo");
    } finally {
      setLoadingEnv(false);
    }
  }

  async function reveal(filePath: string, key: string) {
    if (!selectedRepo) return;
    const mapKey = `${filePath}::${key}`;
    setRevealing(mapKey);
    try {
      const res = await api.post(`/system/repos/${encodeURIComponent(selectedRepo)}/env/reveal`, {
        file_path: filePath,
        key,
      });
      setRevealed((prev) => ({ ...prev, [mapKey]: res.data.value }));
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to reveal value");
    } finally {
      setRevealing(null);
    }
  }

  function hide(filePath: string, key: string) {
    const mapKey = `${filePath}::${key}`;
    setRevealed((prev) => {
      const next = { ...prev };
      delete next[mapKey];
      return next;
    });
  }

  if (role && role !== "admin") return null;

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "Repos & Env" }]} />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-800">Repos & Env</h1>
          <p className="text-sm text-slate-500">
            Browse projects on this server and their <span className="font-mono">.env</span> files.
            Sensitive values (passwords, secrets, keys, tokens) are hidden by default — click Reveal
            to view one at a time. Every reveal is logged.
          </p>
        </div>

        {error && <p className="text-red-600 mb-4">{error}</p>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <div className="card divide-y divide-slate-100 overflow-hidden">
              {loadingRepos && <p className="p-4 text-sm text-slate-500">Loading repos…</p>}
              {!loadingRepos && repos.length === 0 && !error && (
                <p className="p-4 text-sm text-slate-500">No repos found.</p>
              )}
              {repos.map((r) => (
                <button
                  key={r.name}
                  onClick={() => openRepo(r.name)}
                  className={`w-full text-left px-4 py-3 text-sm transition-colors ${
                    selectedRepo === r.name
                      ? "bg-brand-50 text-brand-700 font-medium"
                      : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  {r.name}
                </button>
              ))}
            </div>
          </div>

          <div className="md:col-span-2">
            {!selectedRepo && (
              <div className="card p-10 text-center text-slate-500 text-sm">
                Select a repo on the left to view its .env files.
              </div>
            )}

            {selectedRepo && loadingEnv && (
              <p className="text-sm text-slate-500">Loading .env files for {selectedRepo}…</p>
            )}

            {selectedRepo && !loadingEnv && envFiles.length === 0 && !error && (
              <div className="card p-10 text-center text-slate-500 text-sm">
                No .env files found for this repo (checked .env, backend/.env, frontend/.env).
              </div>
            )}

            {selectedRepo &&
              !loadingEnv &&
              envFiles.map((file) => (
                <div key={file.file_path} className="card p-0 overflow-hidden mb-4">
                  <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                    <span className="text-sm font-mono text-slate-700">
                      {selectedRepo}/{file.file_path}
                    </span>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {file.keys.map((k) => {
                      const mapKey = `${file.file_path}::${k.key}`;
                      const isRevealed = mapKey in revealed;
                      const isBusy = revealing === mapKey;
                      return (
                        <div
                          key={k.key}
                          className="px-4 py-2.5 flex items-center justify-between gap-4 text-sm"
                        >
                          <span className="font-mono text-slate-600 shrink-0">{k.key}</span>
                          <div className="flex items-center gap-2 min-w-0">
                            {!k.is_sensitive ? (
                              <span className="font-mono text-slate-800 truncate">
                                {k.value || <span className="text-slate-400">(empty)</span>}
                              </span>
                            ) : isRevealed ? (
                              <>
                                <span className="font-mono text-red-700 truncate">
                                  {revealed[mapKey]}
                                </span>
                                <button
                                  onClick={() => hide(file.file_path, k.key)}
                                  className="text-xs text-slate-400 hover:text-slate-600 shrink-0"
                                >
                                  Hide
                                </button>
                              </>
                            ) : (
                              <>
                                <span className="font-mono text-slate-400 tracking-widest">
                                  ••••••••
                                </span>
                                <button
                                  disabled={isBusy}
                                  onClick={() => reveal(file.file_path, k.key)}
                                  className="text-xs text-brand-600 hover:text-brand-700 shrink-0"
                                >
                                  {isBusy ? "…" : "Reveal"}
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </main>
    </div>
  );
}
