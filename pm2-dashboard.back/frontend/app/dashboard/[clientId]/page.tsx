"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ClientItem, ServerItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import ServerCard from "@/components/ServerCard";
import AddServerModal from "@/components/AddServerModal";

export default function ClientServersPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [client, setClient] = useState<ClientItem | null>(null);
  const [servers, setServers] = useState<ServerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
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
    } catch (err) {
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
    <div className="min-h-screen">
      <Navbar crumbs={client ? [{ label: client.name }] : []} />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">
              {client ? client.name : "Servers"}
            </h1>
            <p className="text-sm text-slate-500">Select a server to view its PM2 processes</p>
          </div>
          {role === "admin" && (
            <button className="btn-primary" onClick={() => setShowAddModal(true)}>
              + Add Server
            </button>
          )}
        </div>

        {loading && <p className="text-slate-500">Loading servers…</p>}
        {error && <p className="text-red-600">{error}</p>}

        {!loading && servers.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No servers yet for this client. {role === "admin" ? "Add one to get started." : ""}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {servers.map((s) => (
            <ServerCard key={s.id} server={s} />
          ))}
        </div>
      </main>

      {showAddModal && client && (
        <AddServerModal
          clientId={client.id}
          onClose={() => setShowAddModal(false)}
          onCreated={fetchData}
        />
      )}
    </div>
  );
}
