"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, K8sClientItem, K8sClusterItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import K8sClusterCard from "@/components/K8sClusterCard";
import AddClusterModal from "@/components/AddClusterModal";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

export default function K8sClientClustersPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [client, setClient] = useState<K8sClientItem | null>(null);
  const [clusters, setClusters] = useState<K8sClusterItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clientRes, clustersRes] = await Promise.all([
        api.get<K8sClientItem>(`/k8s-clients/${clientId}`),
        api.get<K8sClusterItem[]>("/k8s-clusters", { params: { client_id: clientId } }),
      ]);
      setClient(clientRes.data);
      setClusters(clustersRes.data);
      setError(null);
    } catch {
      setError("Failed to load clusters");
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
          { label: "Kubernetes Dashboard", href: "/dashboard/k8s" },
          { label: client ? client.name : "Clusters" },
        ]}
      />
      <div className="relative flex-1 overflow-y-auto min-h-0">
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">
              {client ? client.name : "Clusters"}
            </h1>
            <p className="text-sm text-slate-500">Select a cluster to view its pods</p>
          </div>
          {role === "admin" && (
            <button className="btn-primary" onClick={() => setShowAddModal(true)}>
              + Add Cluster
            </button>
          )}
        </div>

        <PageLoadingOverlay show={loading} message="Loading servers" subMessage="Connecting to server registry" />
        {error && <p className="text-red-600">{error}</p>}
        {!loading && clusters.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No Kubernetes clusters yet for this client. {role === "admin" ? "Add one to get started." : ""}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {clusters.map((c) => (
            <K8sClusterCard key={c.id} cluster={c} onDeleted={fetchData} />
          ))}
        </div>
      </main>

      </div>
      {showAddModal && client && (
        <AddClusterModal clientId={client.id} onClose={() => setShowAddModal(false)} onCreated={fetchData} />
      )}
    </div>
  );
}
