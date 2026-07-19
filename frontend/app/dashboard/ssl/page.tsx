"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

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

  const [domains, setDomains] = useState<SslDomainItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanningAll, setScanningAll] = useState(false);
  const [showAllOk, setShowAllOk] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<number | null | "unassigned">(null);

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

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchDomains();
  }, [role, isLoading, router, fetchDomains]);

  async function scanAll() {
    setScanningAll(true);
    try {
      await api.post("/ssl/scan-all");
      await fetchDomains();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Scan failed");
    } finally {
      setScanningAll(false);
    }
  }

  const threshold = 30;

  // Group domains by client for the top-level client list view
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
            </p>
          </div>
          {role === "admin" && (
            <button className="btn-primary text-sm" onClick={scanAll} disabled={scanningAll}>
              {scanningAll ? "Scanning all servers…" : "Refresh all"}
            </button>
          )}
        </div>

        {error && <p className="text-red-600 mb-4">{error}</p>}
        {loading && <p className="text-slate-500">Loading…</p>}

        {!loading && !error && domains.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No domains scanned yet.{" "}
            {role === "admin"
              ? 'Click "Refresh all" above to scan your servers for nginx-configured SSL domains.'
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

        {/* CLIENT DETAIL VIEW */}
        {!loading && selectedGroup && (
          <div>
            <button
              onClick={() => setSelectedClientId(null)}
              className="text-sm text-brand-600 hover:text-brand-800 mb-4 flex items-center gap-1"
            >
              ← Back to all clients
            </button>
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

            <div className="space-y-2">
              {visibleInSelected.map((d) => (
                <div key={d.id} className="card p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{d.domain}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {d.server_name} {d.cert_path && `· ${d.cert_path}`}
                    </p>
                    {d.expires_at && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        Expires {new Date(d.expires_at).toLocaleDateString()} · last checked{" "}
                        {d.last_scanned_at ? new Date(d.last_scanned_at).toLocaleString() : "never"}
                      </p>
                    )}
                  </div>
                  <span className={`badge shrink-0 ml-4 ${statusStyle(d.days_remaining)}`}>
                    {statusLabel(d.days_remaining)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
