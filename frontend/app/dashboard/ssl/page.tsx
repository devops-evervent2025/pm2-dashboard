"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import AddDomainModal from "@/components/AddDomainModal";

interface SslDomainItem {
  id: number;
  server_id: number;
  server_name?: string | null;
  client_id?: number | null;
  client_name?: string | null;
  domain: string;
  cert_path?: string | null;
  expires_at?: string | null;
  days_remaining?: number | null;
  last_scanned_at?: string | null;
}

interface ScanStatus {
  running: boolean;
  started_at: string | null;
  finished_at: string | null;
  servers_total: number;
  servers_done: number;
  current_server: string | null;
  error: string | null;
}

function statusStyle(days: number | null | undefined) {
  if (days === null || days === undefined) return "bg-slate-100 text-slate-600";
  if (days < 0) return "bg-red-100 text-red-700";
  if (days < 14) return "bg-red-100 text-red-700";
  if (days < 30) return "bg-amber-100 text-amber-700";
  return "bg-emerald-100 text-emerald-700";
}

function statusLabel(days: number | null | undefined) {
  if (days === null || days === undefined) return "unknown";
  if (days < 0) return `expired ${Math.abs(days)}d ago`;
  return `${days}d left`;
}

export default function SslDashboardPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();
  const isAdmin = role === "admin";

  const [domains, setDomains] = useState<SslDomainItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [scanElapsed, setScanElapsed] = useState(0);
  const [scanJustSucceeded, setScanJustSucceeded] = useState(false);
  const [showAllOk, setShowAllOk] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<number | null | "unassigned">(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const elapsedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wasRunningRef = useRef(false);

  const fetchDomains = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<SslDomainItem[]>("/ssl/domains");
      setDomains(res.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load SSL domains");
    } finally {
      setLoading(false);
    }
  }, []);

  // Polls scan-status. Reschedules itself while a scan is running, so this
  // keeps tracking real backend progress regardless of refreshes - a scan
  // started in one tab, or by the periodic 2-hour job, shows up here too.
  const pollStatus = useCallback(async () => {
    try {
      const res = await api.get<ScanStatus>("/ssl/scan-status");
      setScanStatus(res.data);

      if (res.data.running) {
        wasRunningRef.current = true;
        pollTimeoutRef.current = setTimeout(pollStatus, 2000);
      } else {
        if (wasRunningRef.current) {
          // A scan that WAS running just finished - reload results.
          wasRunningRef.current = false;
          await fetchDomains();
          setScanJustSucceeded(true);
          setTimeout(() => setScanJustSucceeded(false), 3000);
        }
      }
    } catch {
      // Transient error polling status - keep trying while we still think
      // a scan might be running.
      if (wasRunningRef.current) {
        pollTimeoutRef.current = setTimeout(pollStatus, 3000);
      }
    }
  }, [fetchDomains]);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) {
      fetchDomains();
      pollStatus(); // picks up an already-running scan after a refresh
    }
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
      if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, isLoading, router, fetchDomains]);

  // Elapsed-time ticker, computed from the backend's started_at so it's
  // accurate even if this page was just opened mid-scan.
  useEffect(() => {
    if (elapsedIntervalRef.current) {
      clearInterval(elapsedIntervalRef.current);
      elapsedIntervalRef.current = null;
    }
    if (scanStatus?.running && scanStatus.started_at) {
      const startMs = Date.parse(scanStatus.started_at + "Z");
      const tick = () => setScanElapsed(Math.max(1, Math.round((Date.now() - startMs) / 1000)));
      tick();
      elapsedIntervalRef.current = setInterval(tick, 1000);
    } else {
      setScanElapsed(0);
    }
    return () => {
      if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
    };
  }, [scanStatus?.running, scanStatus?.started_at]);

  async function scanAll() {
    try {
      await api.post("/ssl/scan-all");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to start scan");
      return;
    }
    pollStatus();
  }

  async function handleDelete(id: number, domainName: string) {
    if (!confirm(`Remove "${domainName}" from tracking? This only removes it from the dashboard, not the server.`)) {
      return;
    }
    setDeletingId(id);
    try {
      await api.delete(`/ssl/domains/${id}`);
      setDomains((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to delete domain");
    } finally {
      setDeletingId(null);
    }
  }

  const threshold = 30;

  const clientGroups = useMemo(() => {
    const groups = new Map<string, { clientId: number | "unassigned"; clientName: string; domains: SslDomainItem[] }>();
    for (const d of domains) {
      const key = d.client_id != null ? String(d.client_id) : "unassigned";
      const name = d.client_name || "Unassigned / Unknown client";
      if (!groups.has(key)) {
        groups.set(key, { clientId: d.client_id != null ? d.client_id : "unassigned", clientName: name, domains: [] });
      }
      groups.get(key)!.domains.push(d);
    }
    return Array.from(groups.values()).sort((a, b) => a.clientName.localeCompare(b.clientName));
  }, [domains]);

  const selectedGroup = useMemo(() => {
    if (selectedClientId === null) return null;
    return clientGroups.find((g) => g.clientId === selectedClientId) || null;
  }, [clientGroups, selectedClientId]);

  const visibleInSelected = useMemo(() => {
    if (!selectedGroup) return [];
    return showAllOk
      ? selectedGroup.domains
      : selectedGroup.domains.filter(
          (d) => d.days_remaining === null || d.days_remaining === undefined || d.days_remaining < threshold
        );
  }, [selectedGroup, showAllOk]);

  const scanButtonLabel = scanJustSucceeded
    ? "✓ Scan complete"
    : scanStatus?.running
    ? `Scanning… (${scanElapsed}s${
        scanStatus.servers_total ? ` · ${scanStatus.servers_done}/${scanStatus.servers_total} servers` : ""
      })`
    : "Refresh all";

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "SSL Certificates" }]} />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">SSL Dashboard</h1>
            <p className="text-sm text-slate-500">
              Domains and certificates are auto-detected from each server&apos;s nginx conf folder,
              grouped by client. Each certificate is checked directly over HTTPS, per domain.
              Scans also run automatically every 2 hours.
            </p>
          </div>
          {isAdmin && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                className="text-sm px-4 py-2 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50"
                onClick={() => setAddModalOpen(true)}
              >
                + Add domain
              </button>
              <button
                className={`btn-primary text-sm ${scanStatus?.running ? "cursor-not-allowed opacity-70" : ""}`}
                onClick={scanAll}
                disabled={!!scanStatus?.running}
              >
                {scanButtonLabel}
              </button>
            </div>
          )}
        </div>

        {error && <p className="text-red-600 mb-4">{error}</p>}
        {loading && <p className="text-slate-500">Loading…</p>}

        {!loading && !error && domains.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No domains scanned yet.{" "}
            {isAdmin
              ? 'Click "Refresh all" above to scan your servers for nginx-configured SSL domains, or add one manually.'
              : "Ask an admin to run a scan."}
          </div>
        )}

        {/* CLIENT LIST VIEW */}
        {!loading && !selectedGroup && domains.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {clientGroups.map((g) => {
              const expiringSoon = g.domains.filter(
                (d) => d.days_remaining !== null && d.days_remaining !== undefined && d.days_remaining < 7
              ).length;
              return (
                <button
                  key={String(g.clientId)}
                  onClick={() => setSelectedClientId(g.clientId)}
                  className="card p-5 text-left hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <h3 className="text-base font-semibold text-slate-800">{g.clientName}</h3>
                    {expiringSoon > 0 && (
                      <span className="badge bg-red-100 text-red-700 shrink-0 ml-2">
                        {expiringSoon} expiring
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-500 mt-1">{g.domains.length} domain(s)</p>
                </button>
              );
            })}
          </div>
        )}

        {/* CLIENT DETAIL VIEW — dynamic table */}
        {!loading && selectedGroup && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setSelectedClientId(null)}
                className="text-sm text-brand-600 hover:text-brand-800 flex items-center gap-1"
              >
                ← Back to all clients
              </button>
              {isAdmin && (
                <button
                  className="text-sm px-4 py-2 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50"
                  onClick={() => setAddModalOpen(true)}
                >
                  + Add domain to {selectedGroup.clientName}
                </button>
              )}
            </div>

            <h2 className="text-lg font-semibold text-slate-800 mb-3">{selectedGroup.clientName}</h2>

            <label className="flex items-center gap-2 text-sm text-slate-600 mb-4">
              <input
                type="checkbox"
                checked={showAllOk}
                onChange={(e) => setShowAllOk(e.target.checked)}
              />
              Show all domains (including ones that are OK, well within their alert threshold)
            </label>

            {visibleInSelected.length === 0 && (
              <div className="card p-10 text-center text-emerald-600">
                All certificates for this client are healthy and well within their expiry threshold.
              </div>
            )}

            {visibleInSelected.length > 0 && (
              <div className="card overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-slate-500">
                      <th className="px-4 py-3 font-medium">Domain</th>
                      <th className="px-4 py-3 font-medium">Server</th>
                      <th className="px-4 py-3 font-medium">Cert path</th>
                      <th className="px-4 py-3 font-medium">Expires</th>
                      <th className="px-4 py-3 font-medium">Last checked</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      {isAdmin && <th className="px-4 py-3 font-medium text-right">Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {visibleInSelected.map((d) => (
                      <tr key={d.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                        <td className="px-4 py-3 font-medium text-slate-800">{d.domain}</td>
                        <td className="px-4 py-3 text-slate-600">{d.server_name || "—"}</td>
                        <td className="px-4 py-3 text-slate-500 max-w-[220px] truncate" title={d.cert_path || ""}>
                          {d.cert_path || "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {d.expires_at ? new Date(d.expires_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-500">
                          {d.last_scanned_at ? new Date(d.last_scanned_at).toLocaleString() : "never"}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`badge ${statusStyle(d.days_remaining)}`}>
                            {statusLabel(d.days_remaining)}
                          </span>
                        </td>
                        {isAdmin && (
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleDelete(d.id, d.domain)}
                              disabled={deletingId === d.id}
                              className="text-xs text-red-600 hover:text-red-800 disabled:opacity-50"
                            >
                              {deletingId === d.id ? "Removing…" : "Delete"}
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      {isAdmin && (
        <AddDomainModal
          open={addModalOpen}
          onClose={() => setAddModalOpen(false)}
          onAdded={fetchDomains}
          clientId={selectedClientId}
        />
      )}
    </div>
  );
}
