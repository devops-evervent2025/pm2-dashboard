"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, ClientItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import AppLogsClientCard from "@/components/AppLogsClientCard";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

export default function AppLogsClientsPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<ClientItem[]>("/clients");
      setClients(res.data);
      setError(null);
    } catch {
      setError("Failed to load clients");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchClients();
  }, [role, isLoading, router, fetchClients]);

  return (
    <div className="flex flex-col h-full min-h-0">
      <Navbar />
      <div className="relative flex-1 overflow-y-auto min-h-0">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">App Logs</h1>
        <p className="text-sm text-slate-500 mb-6">Select a client to view its servers</p>

        <PageLoadingOverlay show={loading} message="Loading clients" subMessage="Fetching client list from dashboard" />
        {error && <p className="text-red-600">{error}</p>}

        {!loading && clients.length === 0 && (
          <div className="card p-10 text-center text-slate-500">No clients yet.</div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients.map((c) => (
            <AppLogsClientCard key={c.id} client={c} />
          ))}
        </div>
      </main>
      </div>
    </div>
  );
}
