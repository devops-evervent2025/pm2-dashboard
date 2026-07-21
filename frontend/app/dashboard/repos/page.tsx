"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, RepoItem, EnvFileItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

interface ScanPath {
  id: number;
  server_id: number;
  server_name?: string | null;
  base_path: string;
  label?: string | null;
}

interface ServerItem {
  id: number;
  client_id: number;
  name: string;
}

interface ClientItem {
  id: number;
  name: string;
}

interface UnifiedRepo {
  key: string;
  name: string;
  source: "local" | { scanPathId: number; serverName: string; basePath: string; label?: string | null };
}

const LOCAL_CLIENT_KEY = "local";

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      className={`w-3.5 h-3.5 transition-transform shrink-0 ${open ? "rotate-180" : ""}`}
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
      <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  );
}

export default function ReposPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  // -------- meta (हल्का data, कोई SSH नहीं) --------
  const [localRepos, setLocalRepos] = useState<RepoItem[]>([]);
  const [scanPaths, setScanPaths] = useState<ScanPath[]>([]);
  const [servers, setServers] = useState<ServerItem[]>([]);
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // -------- client चुनना --------
  // null = clients की grid दिख रही है; "local" या client.id = उसी की repo list
  const [selectedClientKey, setSelectedClientKey] = useState<number | "local" | null>(null);
  const [loadingClientRepos, setLoadingClientRepos] = useState(false);

  // सिर्फ उन्हीं scan paths के repos cache होते हैं जो actually खोले गए हों
  const [remoteReposByScanPath, setRemoteReposByScanPath] = useState<Record<number, RepoItem[]>>({});

  // -------- repo/env viewer --------
  const [selected, setSelected] = useState<UnifiedRepo | null>(null);
  const [envFiles, setEnvFiles] = useState<EnvFileItem[]>([]);
  const [loadingEnv, setLoadingEnv] = useState(false);
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  const [showManage, setShowManage] = useState(false);
  const [scanningAll, setScanningAll] = useState(false);
  const [newServerId, setNewServerId] = useState<number | "">("");
  const [newBasePath, setNewBasePath] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [addingScanPath, setAddingScanPath] = useState(false);

  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // सिर्फ हल्का data - कोई SSH यहाँ नहीं होती, इसलिए यह पूरे page load पर
  // हमेशा तुरंत चलता है, चाहे कितने भी scan paths क्यों न हों
  const loadMeta = useCallback(async () => {
    setLoadingMeta(true);
    setError(null);
    try {
      const [localRes, scanPathsRes, serversRes, clientsRes] = await Promise.all([
        api.get<RepoItem[]>("/system/repos"),
        api.get<ScanPath[]>("/remote-repos/scan-paths"),
        api.get<ServerItem[]>("/servers"),
        api.get<ClientItem[]>("/clients"),
      ]);
      setLocalRepos(localRes.data);
      setScanPaths(scanPathsRes.data);
      setServers(serversRes.data);
      setClients(clientsRes.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load repos");
    } finally {
      setLoadingMeta(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) loadMeta();
  }, [role, isLoading, router, loadMeta]);

  const serverToClient: Record<number, number> = {};
  for (const s of servers) serverToClient[s.id] = s.client_id;

  function scanPathsForClient(clientKey: number | "local"): ScanPath[] {
    if (clientKey === "local") return [];
    return scanPaths.filter((sp) => serverToClient[sp.server_id] === clientKey);
  }

  // सिर्फ चुने हुए client के scan paths के लिए ही SSH calls जाती हैं - बाकी
  // किसी और client को छुआ तक नहीं जाता, इसलिए एक साथ कई clients खोलने पर भी
  // हर client अपनी सीमित मात्रा में ही SSH connections खोलता है
  async function openClient(clientKey: number | "local") {
    setSelectedClientKey(clientKey);
    setSelected(null);
    setEnvFiles([]);
    setOpenGroup(null);
    setSearchQuery("");

    if (clientKey === "local") return;

    const relevantScanPaths = scanPathsForClient(clientKey);
    const toFetch = relevantScanPaths.filter((sp) => !(sp.id in remoteReposByScanPath));
    if (toFetch.length === 0) return;

    setLoadingClientRepos(true);
    try {
      const results = await Promise.all(
        toFetch.map((sp) =>
          api
            .get<RepoItem[]>(`/remote-repos/scan-paths/${sp.id}/repos`)
            .then((res) => ({ id: sp.id, repos: res.data }))
            .catch(() => ({ id: sp.id, repos: [] as RepoItem[] }))
        )
      );
      setRemoteReposByScanPath((prev) => {
        const next = { ...prev };
        for (const { id, repos } of results) next[id] = repos;
        return next;
      });
    } finally {
      setLoadingClientRepos(false);
    }
  }

  function backToClients() {
    setSelectedClientKey(null);
    setSelected(null);
    setEnvFiles([]);
  }

  function envUrlFor(repo: UnifiedRepo, suffix: string): string {
    if (repo.source === "local") {
      return `/system/repos/${encodeURIComponent(repo.name)}/env${suffix}`;
    }
    return `/remote-repos/scan-paths/${repo.source.scanPathId}/repos/${encodeURIComponent(
      repo.name
    )}/env${suffix}`;
  }

  async function openRepo(repo: UnifiedRepo) {
    setSelected(repo);
    setEnvFiles([]);
    setRevealed({});
    setLoadingEnv(true);
    try {
      const res = await api.get<EnvFileItem[]>(envUrlFor(repo, ""));
      setEnvFiles(res.data);
      setError(null);

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
  }

  function fileAsText(file: EnvFileItem): string {
    return file.keys
      .map((k) => {
        const mapKey = `${file.file_path}::${k.key}`;
        const value = k.is_sensitive ? revealed[mapKey] ?? "••••••••" : k.value ?? "";
        return `${k.key}=${value}`;
      })
      .join("\n");
  }

  async function copyFile(file: EnvFileItem) {
    try {
      await navigator.clipboard.writeText(fileAsText(file));
      setCopiedFile(file.file_path);
      setTimeout(() => setCopiedFile(null), 1500);
    } catch {
      alert("Could not copy - your browser may be blocking clipboard access.");
    }
  }

  async function addScanPath() {
    if (!newServerId || !newBasePath.trim()) return;
    setAddingScanPath(true);
    try {
      await api.post("/remote-repos/scan-paths", {
        server_id: newServerId,
        base_path: newBasePath.trim(),
        label: newLabel.trim() || null,
      });
      setNewServerId("");
      setNewBasePath("");
      setNewLabel("");
      await loadMeta();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to add scan path");
    } finally {
      setAddingScanPath(false);
    }
  }

  async function removeScanPath(id: number) {
    if (!confirm("Remove this scan path? (This only stops scanning it here - nothing is deleted on the server.)")) return;
    await api.delete(`/remote-repos/scan-paths/${id}`);
    setRemoteReposByScanPath((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    await loadMeta();
  }

  async function scanAllRepos() {
    setScanningAll(true);
    try {
      await api.post("/remote-repos/scan-all");
      setRemoteReposByScanPath({});
      await loadMeta();
      if (selectedClientKey && selectedClientKey !== "local") {
        await openClient(selectedClientKey);
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Scan failed");
    } finally {
      setScanningAll(false);
    }
  }

  function groupLabel(source: UnifiedRepo["source"]): string {
    if (source === "local") return "Local (this server)";
    if (source.label) return `${source.serverName} · ${source.label}`;
    return `${source.serverName} · ${source.basePath}`;
  }

  function toggleGroup(label: string) {
    setOpenGroup((prev) => (prev === label ? null : label));
  }

  // चुने हुए client के हिसाब से ही unifiedRepos बनते हैं - बाकी सब कुछ
  // छुआ तक नहीं जाता
  function buildUnifiedReposForSelected(): UnifiedRepo[] {
    if (selectedClientKey === "local") {
      return localRepos.map((r) => ({ key: `local::${r.name}`, name: r.name, source: "local" as const }));
    }
    if (selectedClientKey === null) return [];
    const relevantScanPaths = scanPathsForClient(selectedClientKey);
    const items: UnifiedRepo[] = [];
    for (const sp of relevantScanPaths) {
      const repos = remoteReposByScanPath[sp.id] || [];
      for (const r of repos) {
        items.push({
          key: `remote-${sp.id}::${r.name}`,
          name: r.name,
          source: {
            scanPathId: sp.id,
            serverName: sp.server_name || `Server #${sp.server_id}`,
            basePath: sp.base_path,
            label: sp.label,
          },
        });
      }
    }
    return items;
  }

  if (role && role !== "admin" && role !== "developer" && role !== "viewer") return null;

  const clientCards: { key: number | "local"; name: string }[] = [
    { key: LOCAL_CLIENT_KEY, name: "Local (this server)" },
    ...clients.map((c) => ({ key: c.id, name: c.name })),
  ];

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "Repos & Env" }]} />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Repos & Env</h1>
            <p className="text-sm text-slate-500">
              Browse projects on this dashboard host and on any managed remote server, and view
              their <span className="font-mono">.env</span> files. Sensitive values are hidden by
              default — click Reveal to view one at a time. Every reveal is logged. This is a
              read-only view; values can't be edited here.
            </p>
          </div>
          {role === "admin" && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                className="btn-primary text-xs whitespace-nowrap"
                onClick={scanAllRepos}
                disabled={scanningAll}
              >
                {scanningAll ? "Scanning…" : "Scan all repos now"}
              </button>
              <button className="btn-secondary text-xs whitespace-nowrap" onClick={() => setShowManage((v) => !v)}>
                {showManage ? "Hide scan paths" : "Manage remote scan paths"}
              </button>
            </div>
          )}
        </div>

        {showManage && role === "admin" && (
          <div className="card p-4 mb-6">
            <h2 className="text-sm font-medium text-slate-700 mb-3">Remote scan paths</h2>
            <p className="text-xs text-slate-400 mb-3">
              If a server hosts more than one environment for the same repo (e.g. Staging and
              Production side by side), add a separate scan path for each with a distinct label
              (e.g. "Staging", "Production") so they show as separate groups.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 mb-3">
              <select
                className="input-field text-sm"
                value={newServerId}
                onChange={(e) => setNewServerId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Select server…</option>
                {servers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <input
                className="input-field text-sm"
                placeholder="Base path e.g. /var/www/Staging"
                value={newBasePath}
                onChange={(e) => setNewBasePath(e.target.value)}
              />
              <input
                className="input-field text-sm"
                placeholder="Label e.g. Staging"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
              />
              <button
                className="btn-primary text-sm"
                onClick={addScanPath}
                disabled={addingScanPath || !newServerId || !newBasePath.trim()}
              >
                {addingScanPath ? "Adding…" : "+ Add"}
              </button>
            </div>
            {scanPaths.length === 0 ? (
              <p className="text-xs text-slate-400">No remote scan paths configured yet.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {scanPaths.map((sp) => (
                  <div key={sp.id} className="py-2 flex items-center justify-between text-sm">
                    <span>
                      <span className="font-medium">{sp.server_name}</span>
                      <span className="text-slate-400"> · {sp.base_path}</span>
                      {sp.label && <span className="text-slate-400"> · {sp.label}</span>}
                    </span>
                    <button
                      className="text-xs text-red-600 hover:text-red-700"
                      onClick={() => removeScanPath(sp.id)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {error && <p className="text-red-600 mb-4">{error}</p>}

        {selectedClientKey === null ? (
          // -------- Step 1: सिर्फ clients की grid, कोई SSH नहीं हुई अभी तक --------
          <>
            {loadingMeta && <p className="text-sm text-slate-500">Loading clients…</p>}
            {!loadingMeta && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {clientCards.map((c) => (
                  <button
                    key={c.key}
                    onClick={() => openClient(c.key)}
                    className="card p-5 text-left hover:shadow-md transition-shadow flex items-center gap-3"
                  >
                    <span className="w-10 h-10 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center shrink-0">
                      <FolderIcon />
                    </span>
                    <span className="font-medium text-slate-800">{c.name}</span>
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          // -------- Step 2: चुने हुए client के repos/env --------
          <>
            <button
              onClick={backToClients}
              className="text-sm text-brand-600 hover:text-brand-700 mb-4 inline-flex items-center gap-1"
            >
              ← Back to clients
            </button>

            <div className="mb-4">
              <input
                type="text"
                placeholder="Search repos in this client…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field text-sm w-full max-w-md"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-1">
                <div className="card divide-y divide-slate-100 overflow-hidden">
                  {loadingClientRepos && (
                    <p className="p-4 text-sm text-slate-500">Loading repos for this client…</p>
                  )}
                  {!loadingClientRepos &&
                    (() => {
                      const unifiedRepos = buildUnifiedReposForSelected();
                      const q = searchQuery.trim().toLowerCase();
                      const filtered = q
                        ? unifiedRepos.filter(
                            (r) =>
                              groupLabel(r.source).toLowerCase().includes(q) ||
                              r.name.toLowerCase().includes(q)
                          )
                        : unifiedRepos;

                      const grouped = Object.entries(
                        filtered.reduce<Record<string, UnifiedRepo[]>>((acc, r) => {
                          const label = groupLabel(r.source);
                          (acc[label] = acc[label] || []).push(r);
                          return acc;
                        }, {})
                      );

                      if (grouped.length === 0) {
                        return (
                          <p className="p-4 text-sm text-slate-500">
                            {q ? `No repos match "${searchQuery}".` : "No repos found for this client."}
                          </p>
                        );
                      }

                      return grouped.map(([label, repos]) => {
                        const isCollapsed = q ? false : openGroup !== label;
                        return (
                          <div key={label}>
                            <button
                              onClick={() => toggleGroup(label)}
                              className="w-full flex items-center gap-2 px-4 py-2.5 bg-slate-50 text-left text-xs font-medium text-slate-500 tracking-wide hover:bg-slate-100"
                            >
                              <ChevronIcon open={!isCollapsed} />
                              {label}
                              <span className="ml-auto font-normal text-slate-400">{repos.length}</span>
                            </button>
                            {!isCollapsed &&
                              repos.map((r) => (
                                <button
                                  key={r.key}
                                  onClick={() => openRepo(r)}
                                  className={`w-full text-left px-4 py-2.5 pl-8 text-sm transition-colors ${
                                    selected?.key === r.key
                                      ? "bg-brand-50 text-brand-700 font-medium"
                                      : "hover:bg-slate-50 text-slate-700"
                                  }`}
                                >
                                  {r.name}
                                </button>
                              ))}
                          </div>
                        );
                      });
                    })()}
                </div>
              </div>

              <div className="md:col-span-2">
                {!selected && (
                  <div className="card p-10 text-center text-slate-500 text-sm">
                    Select a repo on the left to view its .env files.
                  </div>
                )}

                {selected && loadingEnv && (
                  <p className="text-sm text-slate-500">Loading .env files for {selected.name}…</p>
                )}

                {selected && !loadingEnv && envFiles.length === 0 && !error && (
                  <div className="card p-10 text-center text-slate-500 text-sm">
                    No .env files found for this repo (checked .env, backend/.env, frontend/.env).
                  </div>
                )}

                {selected &&
                  !loadingEnv &&
                  envFiles.map((file) => (
                    <div key={file.file_path} className="card p-0 overflow-hidden mb-4">
                      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                        <span className="text-sm font-mono text-slate-700">
                          {selected.name}/{file.file_path}
                        </span>
                        <button
                          onClick={() => copyFile(file)}
                          className="text-xs text-brand-600 hover:text-brand-700 shrink-0"
                        >
                          {copiedFile === file.file_path ? "Copied!" : "Copy"}
                        </button>
                      </div>
                      <div className="bg-slate-900 text-slate-100 font-mono text-xs p-4 overflow-x-auto">
                        {file.keys.map((k) => {
                          const mapKey = `${file.file_path}::${k.key}`;
                          const value = k.is_sensitive ? revealed[mapKey] : k.value;
                          return (
                            <div key={k.key} className="whitespace-pre flex items-center gap-2 py-0.5">
                              <span className="text-sky-400">{k.key}</span>
                              <span className="text-slate-500">=</span>
                              <span className={k.is_sensitive ? "text-amber-300" : "text-emerald-300"}>
                                {value || <span className="text-slate-500 italic">(empty)</span>}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
