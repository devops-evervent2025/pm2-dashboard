"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import { api, ServerItem } from "@/lib/api";
import ServerLogsBrowser from "@/components/ServerLogsBrowser";

export default function AppLogsPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [servers, setServers] = useState<ServerItem[]>([]);
  const [serverId, setServerId] = useState<number | "">("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
    }
  }, [role, isLoading, router]);

  const loadServers = useCallback(async () => {
    try {
      const res = await api.get<ServerItem[]>("/servers");
      setServers(res.data);
    } catch {
      setLoadError("Could not load servers.");
    }
  }, []);

  useEffect(() => {
    if (role) loadServers();
  }, [role, loadServers]);

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">App Logs</h1>
        <p className="text-sm text-slate-500 mb-6">
          Browse, view, and download log files from a managed server's configured log
          directories over its existing SSH connection.
        </p>

        <div className="card p-6 mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1">Server</label>
          <select
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            value={serverId}
            onChange={(e) => setServerId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select a server...</option>
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.ip_address})
              </option>
            ))}
          </select>
          {loadError && <p className="text-sm text-red-600 mt-2">{loadError}</p>}
        </div>

        {serverId ? (
          <ServerLogsBrowser serverId={Number(serverId)} />
        ) : (
          <div className="card p-10 text-center text-slate-400 text-sm">
            Select a server above to browse its log files.
          </div>
        )}
      </main>
    </div>
  );
}
