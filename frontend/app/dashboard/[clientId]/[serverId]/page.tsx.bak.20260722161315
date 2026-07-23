"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ServerItem, PM2ProcessItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import ProcessCard from "@/components/ProcessCard";
import EnvBadge from "@/components/EnvBadge";

export default function ServerProcessesPage() {
  const { clientId, serverId } = useParams<{ clientId: string; serverId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [server, setServer] = useState<ServerItem | null>(null);
  const [processes, setProcesses] = useState<PM2ProcessItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="min-h-screen">
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

        {loading && <p className="text-slate-500">Loading processes…</p>}
        {error && <p className="text-red-600">{error}</p>}

        {!loading && !error && processes.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No PM2 processes found on this server.
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {processes.map((p) => (
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
  );
}
