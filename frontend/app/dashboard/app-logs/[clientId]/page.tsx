"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ClientItem, ServerItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import AppLogsServerCard from "@/components/AppLogsServerCard";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

export default function AppLogsClientServersPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [client, setClient] = useState<ClientItem | null>(null);
  const [servers, setServers] = useState<ServerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clientRes, serversRes] = await Promise.all([
        api.get<ClientItem>(`/clients/${clientId}`),
        api.get<ServerItem[]>("/servers", { params: { client_id: clientId } }),
      ]);
      setClient(clientRes.data);
      setServers(serversRes.data);
      setError(null);
    } catch {
      setError("Failed to load servers");
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchData();
  }, [role, isLoading, router, fetchData]);

  return (
    <div className="flex flex-col h-full min-h-0">
      <Navbar
        crumbs={[
          { label: "App Logs", href: "/dashboard/app-logs" },
          { label: client ? client.name : "Servers" },
        ]}
      />
      <div className="relative flex-1 overflow-y-auto min-h-0">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">
          {client ? client.name : "Servers"}
        </h1>
        <p className="text-sm text-slate-500 mb-6">Select a server to view its logs</p>

        <PageLoadingOverlay show={loading} message="Loading servers" subMessage="Connecting to server registry" />
        {error && <p className="text-red-600">{error}</p>}

        {!loading && servers.length === 0 && (
          <div className="card p-10 text-center text-slate-500">No servers yet for this client.</div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {servers.map((s) => (
            <AppLogsServerCard key={s.id} server={s} />
          ))}
        </div>
      </main>
      </div>
    </div>
  );
}
