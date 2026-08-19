"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ServerItem, DockerContainerItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import DockerContainerCard from "@/components/DockerContainerCard";
import EnvBadge from "@/components/EnvBadge";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

export default function DockerServerContainersPage() {
  const { clientId, serverId } = useParams<{ clientId: string; serverId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [server, setServer] = useState<ServerItem | null>(null);
  const [containers, setContainers] = useState<DockerContainerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [serverRes, containerRes] = await Promise.all([
        api.get<ServerItem>(`/servers/${serverId}`),
        api.get<DockerContainerItem[]>(`/servers/${serverId}/containers`),
      ]);
      setServer(serverRes.data);
      setContainers(containerRes.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load Docker containers");
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

  useEffect(() => {
    if (!role) return;
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [role, fetchData]);

  return (
    <div className="flex flex-col h-full min-h-0">
      <Navbar
        crumbs={
          server
            ? [
                { label: "Docker Dashboard", href: "/dashboard/docker" },
                { label: "…", href: `/dashboard/docker/${clientId}` },
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
              {server ? server.name : "Docker Containers"}
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

        <PageLoadingOverlay show={loading} message="Loading" subMessage="Fetching data from remote servers" />
        {error && <p className="text-red-600">{error}</p>}
        {!loading && !error && containers.length === 0 && (
          <div className="card p-10 text-center text-slate-500">
            No Docker containers found on this server.
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {containers.map((c) => (
            <DockerContainerCard
              key={c.id}
              serverId={Number(serverId)}
              clientId={Number(clientId)}
              container={c}
              onAction={fetchData}
            />
          ))}
        </div>
      </main>
      </div>
    </div>
  );
}
