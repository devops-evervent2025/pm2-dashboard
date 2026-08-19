"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, RepoItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import BuildLogTerminal from "@/components/BuildLogTerminal";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

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
  scanPathId: number;
  serverName: string;
  basePath: string;
  label?: string | null;
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={`w-3.5 h-3.5 transition-transform shrink-0 ${open ? "rotate-180" : ""}`}>
      <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
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

export default function BuildManagerPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [scanPaths, setScanPaths] = useState<ScanPath[]>([]);
  const [servers, setServers] = useState<ServerItem[]>([]);
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedClientKey, setSelectedClientKey] = useState<number | null>(null);
  const [loadingClientRepos, setLoadingClientRepos] = useState(false);
  const [remoteReposByScanPath, setRemoteReposByScanPath] = useState<Record<number, RepoItem[]>>({});

  const [selected, setSelected] = useState<UnifiedRepo | null>(null);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [running, setRunning] = useState(false);

  const canRun = role === "admin" || role === "developer";

  const loadMeta = useCallback(async () => {
    setLoadingMeta(true);
    setError(null);
    try {
      const [scanPathsRes, serversRes, clientsRes] = await Promise.all([
        api.get<ScanPath[]>("/remote-repos/scan-paths"),
        api.get<ServerItem[]>("/servers"),
        api.get<ClientItem[]>("/clients"),
      ]);
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

  function scanPathsForClient(clientKey: number): ScanPath[] {
    return scanPaths.filter((sp) => serverToClient[sp.server_id] === clientKey);
  }

  async function openClient(clientKey: number) {
    setSelectedClientKey(clientKey);
    setSelected(null);
    setOpenGroup(null);
    setSearchQuery("");

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
  }

  function groupLabel(sp: { serverName: string; basePath: string; label?: string | null }): string {
    if (sp.label) return `${sp.serverName} · ${sp.label}`;
    return `${sp.serverName} · ${sp.basePath}`;
  }

  function buildUnifiedRepos(): UnifiedRepo[] {
    if (selectedClientKey === null) return [];
    const relevantScanPaths = scanPathsForClient(selectedClientKey);
    const items: UnifiedRepo[] = [];
    for (const sp of relevantScanPaths) {
      const repos = remoteReposByScanPath[sp.id] || [];
      for (const r of repos) {
        items.push({
          key: `${sp.id}::${r.name}`,
          name: r.name,
          scanPathId: sp.id,
          serverName: sp.server_name || `Server #${sp.server_id}`,
          basePath: sp.base_path,
          label: sp.label,
        });
      }
    }
    return items;
  }

  if (role && role !== "admin" && role !== "developer" && role !== "viewer") return null;

  return (
    <div className="flex flex-col h-full min-h-0">
      <Navbar crumbs={[{ label: "Build Manager" }]} />
      <div className="relative flex-1 overflow-y-auto min-h-0">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-800">Build Manager</h1>
          <p className="text-sm text-slate-500">
            Pick a repo (same list as Repos &amp; Env) and run <span className="font-mono">git pull &amp;&amp; npm i -f &amp;&amp; npm run build</span> on
            the server it lives on. If the build succeeds and exactly one running pm2 process name matches the repo, that
            process is restarted automatically. Every run is logged.
          </p>
        </div>

        {error && <p className="text-red-600 mb-4">{error}</p>}

        {selectedClientKey === null ? (
          <>
            <PageLoadingOverlay show={loadingMeta} message="Loading clients" subMessage="Preparing repository browser" />
            {!loadingMeta && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {clients.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => openClient(c.id)}
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
          <>
            <button onClick={backToClients} className="text-sm text-brand-600 hover:text-brand-700 mb-4 inline-flex items-center gap-1">
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
                  {loadingClientRepos && <div className="p-4"><LoadingState message="Loading repos" variant="compact" /></div>}
                  {!loadingClientRepos &&
                    (() => {
                      const unifiedRepos = buildUnifiedRepos();
                      const q = searchQuery.trim().toLowerCase();
                      const filtered = q
                        ? unifiedRepos.filter((r) => groupLabel(r).toLowerCase().includes(q) || r.name.toLowerCase().includes(q))
                        : unifiedRepos;
                      const grouped = Object.entries(
                        filtered.reduce<Record<string, UnifiedRepo[]>>((acc, r) => {
                          const label = groupLabel(r);
                          (acc[label] = acc[label] || []).push(r);
                          return acc;
                        }, {})
                      );
                      if (grouped.length === 0) {
                        return <p className="p-4 text-sm text-slate-500">{q ? `No repos match "${searchQuery}".` : "No repos found for this client."}</p>;
                      }
                      return grouped.map(([label, repos]) => {
                        const isCollapsed = q ? false : openGroup !== label;
                        return (
                          <div key={label}>
                            <button
                              onClick={() => setOpenGroup((prev) => (prev === label ? null : label))}
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
                                  onClick={() => {
                                    setSelected(r);
                                    setRunning(false);
                                  }}
                                  className={`w-full text-left px-4 py-2.5 pl-8 text-sm transition-colors ${
                                    selected?.key === r.key ? "bg-brand-50 text-brand-700 font-medium" : "hover:bg-slate-50 text-slate-700"
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
                  <div className="card p-10 text-center text-slate-500 text-sm">Select a repo on the left to build it.</div>
                )}

                {selected && !running && (
                  <div className="card p-6">
                    <p className="text-sm text-slate-600 mb-1">
                      <span className="font-medium">{selected.name}</span>
                      <span className="text-slate-400"> — {groupLabel(selected)}</span>
                    </p>
                    <p className="text-xs text-slate-400 mb-4 font-mono">{selected.basePath}/{selected.name}</p>
                    {canRun ? (
                      <button className="btn-primary text-sm" onClick={() => setRunning(true)}>
                        Build &amp; Restart
                      </button>
                    ) : (
                      <p className="text-xs text-slate-400">Only admin or developer roles can trigger a build.</p>
                    )}
                  </div>
                )}

                {selected && running && (
                  <BuildLogTerminal wsPath={`/build-manager/ws/${selected.scanPathId}/${encodeURIComponent(selected.name)}`} title={selected.name} onClose={() => setRunning(false)} />
                )}
              </div>
            </div>
          </>
        )}
      </main>
      </div>
    </div>
  );
}
