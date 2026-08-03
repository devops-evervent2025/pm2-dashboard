"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ServerItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import ServerLogsBrowser from "@/components/ServerLogsBrowser";

export default function AppLogsServerPage() {
  const { clientId, serverId } = useParams<{ clientId: string; serverId: string }>();
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [server, setServer] = useState<ServerItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchServer = useCallback(async () => {
    try {
      const res = await api.get<ServerItem>(`/servers/${serverId}`);
      setServer(res.data);
      setError(null);
    } catch {
      setError("Failed to load server");
    }
  }, [serverId]);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) fetchServer();
  }, [role, isLoading, router, fetchServer]);

  return (
    <div className="min-h-screen">
      <Navbar
        crumbs={[
          { label: "App Logs", href: "/dashboard/app-logs" },
          { label: "…", href: `/dashboard/app-logs/${clientId}` },
          { label: server ? server.name : "Logs" },
        ]}
      />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-6">
          {server ? server.name : "Logs"}
        </h1>
        {error && <p className="text-red-600 mb-4">{error}</p>}
        <ServerLogsBrowser serverId={Number(serverId)} />
      </main>
    </div>
  );
}
