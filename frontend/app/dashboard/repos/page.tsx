"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, RepoItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import EnvRepoGroupModal, { UnifiedRepo } from "@/components/EnvRepoGroupModal";
import RepoGroupList from "@/components/RepoGroupList";
import { PageLoadingOverlay } from "@/components/Preloader";

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

const LOCAL_CLIENT_KEY = "local";

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

  const [localRepos, setLocalRepos] = useState<RepoItem[]>([]);
  const [scanPaths, setScanPaths] = useState<ScanPath[]>([]);
  const [servers, setServers] = useState<ServerItem[]>([]);
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedClientKey, setSelectedClientKey] = useState<number | "local" | null>(null);
  const [loadingClientRepos, setLoadingClientRepos] = useState(false);
  const [remoteReposByScanPath, setRemoteReposByScanPath] = useState<Record<number, RepoItem[]>>({});

  const [modalGroup, setModalGroup] = useState<{ label: string; repos: UnifiedRepo[] } | null>(null);

  const [showManage, setShowManage] = useState(false);
  const [scanningAll, setScanningAll] = useState(false);
  const [newServerId, setNewServerId] = useState<number | "">("");
  const [newBasePath, setNewBasePath] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [addingScanPath, setAddingScanPath] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

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

  async function openClient(clientKey: number | "local") {
    setSelectedClientKey(clientKey);
    setModalGroup(null);
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
    setModalGroup(null);
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

  function handleScanComplete(scanPathId: number, repoNames: string[]) {
    setRemoteReposByScanPath((prev) => ({
      ...prev,
      [scanPathId]: repoNames.map((name) => ({ name })),
    }));

    setModalGroup((prev) => {
      if (!prev) return prev;
      const source = prev.repos[0]?.source;
      if (source === "local" || source.scanPathId !== scanPathId) return prev;
      return {
        ...prev,
        repos: repoNames.map((name) => ({
          key: `remote-${scanPathId}::${name}`,
          name,
          source,
        })),
      };
    });
  }

  if (role && role !== "admin" && role !== "developer" && role !== "viewer") return null;

  const clientCards: { key: number | "local"; name: string }[] = [
    { key: LOCAL_CLIENT_KEY, name: "Local (this server)" },
    ...clients.map((c) => ({ key: c.id, name: c.name })),
  ];

  const selectedClientName =
    selectedClientKey === "local"
      ? "Local (this server)"
      : clients.find((c) => c.id === selectedClientKey)?.name ?? "Client";

  const unifiedRepos = buildUnifiedReposForSelected();
  const q = searchQuery.trim().toLowerCase();
  const filteredRepos = q
    ? unifiedRepos.filter(
        (r) => groupLabel(r.source).toLowerCase().includes(q) || r.name.toLowerCase().includes(q)
      )
    : unifiedRepos;
  const groupedRepos = Object.entries(
    filteredRepos.reduce<Record<string, UnifiedRepo[]>>((acc, r) => {
      const label = groupLabel(r.source);
      (acc[label] = acc[label] || []).push(r);
      return acc;
    }, {})
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Navbar crumbs={[{ label: "Repos & Env" }]} />
      <div className="relative flex min-h-0 flex-1 flex-col overflow-y-auto">
        <main className={`w-full px-4 py-6 lg:px-6 ${selectedClientKey !== null ? "flex min-h-0 flex-1 flex-col" : ""}`}>
          {selectedClientKey === null && (
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-slate-800">Repos & Env</h1>
              <p className="text-sm text-slate-500">
                Browse projects on this dashboard host and on any managed remote server, and view
                their <span className="font-mono">.env</span> files. Sensitive values are hidden by
                default — click Reveal to view one at a time. Every reveal is logged. This is a
                read-only view; values can&apos;t be edited here.
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
                <button
                  className="btn-secondary text-xs whitespace-nowrap"
                  onClick={() => setShowManage((v) => !v)}
                >
                  {showManage ? "Hide scan paths" : "Manage remote scan paths"}
                </button>
              </div>
            )}
          </div>
          )}

          {selectedClientKey !== null && role === "admin" && (
            <div className="mb-4 flex shrink-0 flex-wrap items-center justify-end gap-2">
              <button
                className="btn-primary text-xs whitespace-nowrap"
                onClick={scanAllRepos}
                disabled={scanningAll}
              >
                {scanningAll ? "Scanning…" : "Scan all repos now"}
              </button>
              <button
                className="btn-secondary text-xs whitespace-nowrap"
                onClick={() => setShowManage((v) => !v)}
              >
                {showManage ? "Hide scan paths" : "Manage remote scan paths"}
              </button>
            </div>
          )}

          {showManage && role === "admin" && (
            <div className="card p-4 mb-6">
              <h2 className="text-sm font-medium text-slate-700 mb-3">Remote scan paths</h2>
              <p className="text-xs text-slate-400 mb-3">
                If a server hosts more than one environment for the same repo (e.g. Staging and
                Production side by side), add a separate scan path for each with a distinct label
                (e.g. &quot;Staging&quot;, &quot;Production&quot;) so they show as separate groups.
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
            <>
              <PageLoadingOverlay show={loadingMeta} message="Loading clients" subMessage="Preparing repository browser" />
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
            <div className="flex min-h-0 flex-1 flex-col">
              <button
                onClick={backToClients}
                className="mb-4 inline-flex shrink-0 items-center gap-1 text-sm text-brand-600 hover:text-brand-700"
              >
                ← Back to clients
              </button>

              <RepoGroupList
                clientName={selectedClientName}
                groupedRepos={groupedRepos}
                loading={loadingClientRepos}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onOpenGroup={(label, repos) => setModalGroup({ label, repos })}
              />
            </div>
          )}
        </main>
      </div>

      {modalGroup && (
        <EnvRepoGroupModal
          groupLabel={modalGroup.label}
          repos={modalGroup.repos}
          onClose={() => setModalGroup(null)}
          onScanComplete={handleScanComplete}
        />
      )}
    </div>
  );
}
