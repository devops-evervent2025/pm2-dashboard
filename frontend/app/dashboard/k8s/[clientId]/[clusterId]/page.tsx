"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, K8sClusterItem, K8sPodItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import K8sPodCard from "@/components/K8sPodCard";

export default function K8sClusterPodsPage() {
  const { clientId, clusterId } = useParams<{ clientId: string; clusterId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [cluster, setCluster] = useState<K8sClusterItem | null>(null);
  const [pods, setPods] = useState<K8sPodItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [clusterRes, podsRes] = await Promise.all([
        api.get<K8sClusterItem>(`/k8s-clusters/${clusterId}`),
        api.get<K8sPodItem[]>(`/k8s-clusters/${clusterId}/pods`),
      ]);
      setCluster(clusterRes.data);
      setPods(podsRes.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load pods");
    } finally {
      setLoading(false);
    }
  }, [clusterId]);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchData();
  }, [role, isLoading, router, fetchData]);

  useEffect(() => {
    if (!role) return;
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [role, fetchData]);

  return (
    <div className="min-h-screen">
      <Navbar
        crumbs={
          cluster
            ? [
                { label: "Kubernetes Dashboard", href: "/dashboard/k8s" },
                { label: "…", href: `/dashboard/k8s/${clientId}` },
                { label: cluster.name },
              ]
            : []
        }
      />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-slate-800">
            {cluster ? cluster.name : "Pods"}
          </h1>
          <button className="btn-secondary text-sm" onClick={fetchData}>
            Refresh
          </button>
        </div>

        {loading && <p className="text-slate-500">Loading pods…</p>}
        {error && <p className="text-red-600">{error}</p>}
        {!loading && !error && pods.length === 0 && (
          <div className="card p-10 text-center text-slate-500">No pods found on this cluster.</div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {pods.map((p) => (
            <K8sPodCard
              key={`${p.namespace}/${p.name}`}
              clusterId={Number(clusterId)}
              clientId={Number(clientId)}
              pod={p}
              onAction={fetchData}
            />
          ))}
        </div>
      </main>
    </div>
  );
}
