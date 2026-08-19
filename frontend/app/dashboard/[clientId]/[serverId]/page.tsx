"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ServerItem, PM2ProcessItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import ProcessCard from "@/components/ProcessCard";
import EnvBadge from "@/components/EnvBadge";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

export default function ServerProcessesPage() {
  const { clientId, serverId } = useParams<{ clientId: string; serverId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [server, setServer] = useState<ServerItem | null>(null);
  const [processes, setProcesses] = useState<PM2ProcessItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [serverRes, procRes] = await Promise.all([
        api.get<ServerItem>(`/servers/${serverId}`),
        api.get<PM2ProcessItem[]>(`/servers/${serverId}/processes`),
      ]);
      setServer(serverRes.data);
      setProcesses(procRes.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load PM2 processes");
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchData();
  }, [role, isLoading, router, fetchData]);

  // Light polling to keep process status roughly fresh.
  useEffect(() => {
    if (!role) return;
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [role, fetchData]);

  const q = searchQuery.trim().toLowerCase();
  const filteredProcesses = q ? processes.filter((p) => p.name.toLowerCase().includes(q)) : processes;

  return (
    <div className="flex flex-col h-full min-h-0">
      <Navbar
        crumbs={
          server
            ? [
                { label: "…", href: `/dashboard/${clientId}` },
                { label: server.name },
              ]
            : []
        }
      />
      <div className="relative flex-1 overflow-y-auto min-h-0">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-800">
              {server ? server.name : "PM2 Processes"}
            </h1>
            {server && <EnvBadge environment={server.environment} />}
          </div>
          <button className="btn-secondary text-sm" onClick={fetchData}>
            Refresh
          </button>
        </div>
        {server && (
          <p className="text-sm text-slate-500 mb-6 font-mono">
            {server.ssh_username}@{server.ip_address}:{server.ssh_port}
          </p>
        )}

        {!loading && !error && processes.length > 0 && (
          <div className="mb-6">
            <input
              type="text"
              placeholder="Search PM2 process name…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field text-sm w-full max-w-md"
            />
          </div>
        )}

        <PageLoadingOverlay show={loading} message="Loading" subMessage="Fetching data from remote servers" />
        {error && <p className="text-red-600">{error}</p>}

        {!loading && !error && processes.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No PM2 processes found on this server.
          </div>
        )}

        {!loading && !error && processes.length > 0 && filteredProcesses.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No processes match &quot;{searchQuery}&quot;.
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProcesses.map((p) => (
            <ProcessCard
              key={p.pm_id}
              serverId={Number(serverId)}
              clientId={Number(clientId)}
              process={p}
              onAction={fetchData}
            />
          ))}
        </div>
      </main>
      </div>
    </div>
  );
}
