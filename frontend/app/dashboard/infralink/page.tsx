"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  fetchInfraLinkAgents,
  createInfraLinkRegistrationToken,
  InfraLinkAgentItem,
  InfraLinkRegistrationTokenItem,
  ServerItem,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

export default function InfraLinkPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [agents, setAgents] = useState<InfraLinkAgentItem[]>([]);
  const [servers, setServers] = useState<ServerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedServerId, setSelectedServerId] = useState<string>("");
  const [generating, setGenerating] = useState(false);
  const [tokenResult, setTokenResult] = useState<InfraLinkRegistrationTokenItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentsResult, serversRes] = await Promise.all([
        fetchInfraLinkAgents(),
        api.get("/servers"),
      ]);
      setAgents(agentsResult);
      setServers(serversRes.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load InfraLink data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (!isLoading && role && role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    if (role === "admin") load();
  }, [role, isLoading, router, load]);

  useEffect(() => {
    if (role !== "admin") return;
    const interval = setInterval(load, 15000); // matches the agent's ~15s heartbeat interval
    return () => clearInterval(interval);
  }, [role, load]);

  async function handleGenerateToken() {
    if (!selectedServerId) return;
    setGenerating(true);
    setError(null);
    setTokenResult(null);
    try {
      const result = await createInfraLinkRegistrationToken(Number(selectedServerId));
      setTokenResult(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to generate registration token.");
    } finally {
      setGenerating(false);
    }
  }

  if (isLoading || role !== "admin") {
    return null;
  }

  const registeredServerIds = new Set(agents.map((a) => a.server_id));
  const unregisteredServers = servers.filter((s) => !registeredServerIds.has(s.id));
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">InfraLink</h1>
          <p className="text-sm text-slate-500">
            Agent-based host management (Phase 1: registration, heartbeat, status)
          </p>
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="rounded-lg border border-slate-200 p-4 flex flex-col gap-3">
          <h2 className="text-sm font-medium text-slate-700">Register a new agent</h2>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={selectedServerId}
              onChange={(e) => setSelectedServerId(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700"
            >
              <option value="">Select a server…</option>
              {unregisteredServers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.ip_address})
                </option>
              ))}
            </select>
            <button
              onClick={handleGenerateToken}
              disabled={!selectedServerId || generating}
              className="badge bg-brand-50 text-brand-600 disabled:opacity-50"
            >
              {generating ? "Generating…" : "Generate registration token"}
            </button>
          </div>

          {tokenResult && (
            <div className="text-xs bg-slate-50 rounded-lg p-3 font-mono break-all">
              <div>Token: {tokenResult.token}</div>
              <div className="text-slate-500 mt-1">
                Expires: {new Date(tokenResult.expires_at).toLocaleString()}
              </div>
              <div className="text-slate-500 mt-2 whitespace-pre-wrap">
                {`On the target server:\nsudo infralink-agent init --api ${apiUrl}\nsudo infralink-agent register --token ${tokenResult.token}\nsudo infralink-agent install`}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-700">Registered agents</h2>
          <button onClick={load} className="badge bg-brand-50 text-brand-600">
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {loading && agents.length === 0 && <p className="text-slate-500">Loading agents…</p>}
        {!loading && agents.length === 0 && (
          <p className="text-slate-500 text-sm">No agents registered yet.</p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const server = servers.find((s) => s.id === agent.server_id);
            return (
              <div key={agent.id} className="rounded-lg border border-slate-200 p-4 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-800">
                    {server?.name || `Server #${agent.server_id}`}
                  </span>
                  <span
                    className={`badge ${
                      agent.status === "online"
                        ? "bg-green-50 text-green-600"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {agent.status}
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  {agent.hostname || "—"} · {agent.os || "—"}
                </div>
                <div className="text-xs text-slate-500">Agent v{agent.agent_version || "—"}</div>
                <div className="text-xs text-slate-500">
                  CPU {agent.cpu_percent?.toFixed(0) ?? "—"}% · RAM {agent.ram_percent?.toFixed(0) ?? "—"}% ·
                  Disk {agent.disk_percent?.toFixed(0) ?? "—"}%
                </div>
                <div className="text-xs text-slate-400">
                  Last seen: {agent.last_seen_at ? new Date(agent.last_seen_at).toLocaleString() : "never"}
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
