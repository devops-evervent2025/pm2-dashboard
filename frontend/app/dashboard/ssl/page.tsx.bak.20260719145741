"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

interface SslDomainItem {
  id: number;
  server_id: number;
  server_name?: string | null;
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
  const visible = showAllOk
    ? domains
    : domains.filter((d) => d.days_remaining === null || d.days_remaining === undefined || d.days_remaining < threshold);

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "SSL Certificates" }]} />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">SSL Dashboard</h1>
            <p className="text-sm text-slate-500">
              Domains and certificates are auto-detected from each server&apos;s nginx conf folder.
              Scanning is on-demand — results are stored and read from the database afterward, no
              repeated SSH connections.
            </p>
          </div>
          {role === "admin" && (
            <button className="btn-primary text-sm" onClick={scanAll} disabled={scanningAll}>
              {scanningAll ? "Scanning all servers…" : "Refresh all"}
            </button>
          )}
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-600 mb-4">
          <input
            type="checkbox"
            checked={showAllOk}
            onChange={(e) => setShowAllOk(e.target.checked)}
          />
          Show all domains (including ones that are OK, well within their alert threshold)
        </label>

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

        {!loading && domains.length > 0 && visible.length === 0 && (
          <div className="card p-10 text-center text-emerald-600">
            All scanned certificates are healthy and well within their expiry threshold.
          </div>
        )}

        <div className="space-y-2">
          {visible.map((d) => (
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
      </main>
    </div>
  );
}
