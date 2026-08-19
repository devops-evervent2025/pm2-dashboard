"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, K8sClientItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import K8sClientCard from "@/components/K8sClientCard";
import AddK8sClientModal from "@/components/AddK8sClientModal";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

export default function K8sDashboardPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();
  const [clients, setClients] = useState<K8sClientItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<K8sClientItem[]>("/k8s-clients");
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
      <Navbar crumbs={[{ label: "Kubernetes Dashboard" }]} />
      <div className="relative flex-1 overflow-y-auto min-h-0">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Kubernetes — Clients</h1>
            <p className="text-sm text-slate-500">Select a client to view its clusters</p>
          </div>
          {role === "admin" && (
            <button className="btn-primary" onClick={() => setShowAddModal(true)}>
              + Add Client
            </button>
          )}
        </div>

        <PageLoadingOverlay show={loading} message="Loading clients" subMessage="Fetching client list from dashboard" />
        {error && <p className="text-red-600">{error}</p>}
        {!loading && clients.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No Kubernetes clients yet. {role === "admin" ? "Add your first one to get started." : ""}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients.map((c) => (
            <K8sClientCard key={c.id} client={c} onDeleted={fetchClients} />
          ))}
        </div>
      </main>

      </div>
      {showAddModal && (
        <AddK8sClientModal onClose={() => setShowAddModal(false)} onCreated={fetchClients} />
      )}
    </div>
  );
}
