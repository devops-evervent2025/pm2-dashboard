"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ClientItem, ServerItem, PM2ProcessItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

interface ProcessAlert {
  type: "process";
  clientId: number;
  clientName: string;
  serverId: number;
  serverName: string;
  process: PM2ProcessItem;
}

interface ServerAlert {
  type: "server_unreachable";
  clientId: number;
  clientName: string;
  serverId: number;
  serverName: string;
  detail: string;
}

type Alert = ProcessAlert | ServerAlert;

const REFRESH_INTERVAL_MS = 30000;

export default function AlertsPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [healthyCount, setHealthyCount] = useState(0);
  const [serverCount, setServerCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const runScan = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    setScanError(null);

    try {
      const clientsRes = await api.get<ClientItem[]>("/clients");
      const clients = clientsRes.data;

      const collected: Alert[] = [];
      let healthy = 0;
      let servers = 0;

      await Promise.all(
        clients.map(async (client) => {
          let clientServers: ServerItem[] = [];
          try {
            const serversRes = await api.get<ServerItem[]>("/servers", {
              params: { client_id: client.id },
            });
            clientServers = serversRes.data;
          } catch {
            return;
          }

          await Promise.all(
            clientServers.map(async (server) => {
              servers += 1;
              try {
                const procRes = await api.get<PM2ProcessItem[]>(
                  `/servers/${server.id}/processes`
                );
                for (const proc of procRes.data) {
                  if (proc.status === "online") {
                    healthy += 1;
                  } else {
                    collected.push({
                      type: "process",
                      clientId: client.id,
                      clientName: client.name,
                      serverId: server.id,
                      serverName: server.name,
                      process: proc,
                    });
                  }
                }
              } catch (err: any) {
                collected.push({
                  type: "server_unreachable",
                  clientId: client.id,
                  clientName: client.name,
                  serverId: server.id,
                  serverName: server.name,
                  detail: err?.response?.data?.detail || "Could not reach this server.",
                });
              }
            })
          );
        })
      );

      setAlerts(collected);
      setHealthyCount(healthy);
      setServerCount(servers);
      setLastChecked(new Date());
    } catch (err: any) {
      setScanError(err?.response?.data?.detail || "Failed to run the alerts scan.");
    } finally {
      setLoading(false);
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (role) runScan();
  }, [role, isLoading, router, runScan]);

  useEffect(() => {
    if (!role) return;
    const interval = setInterval(runScan, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [role, runScan]);

  const processAlerts = alerts.filter((a): a is ProcessAlert => a.type === "process");
  const serverAlerts = alerts.filter((a): a is ServerAlert => a.type === "server_unreachable");

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "Alerts" }]} />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Alerts</h1>
            <p className="text-sm text-slate-500">
              Any PM2 process that isn&apos;t <span className="font-mono">online</span>, or any
              server we couldn&apos;t reach, shows up here across all clients.
            </p>
          </div>
          <button className="btn-secondary text-sm" onClick={runScan} disabled={loading}>
            {loading ? "Scanning…" : "Refresh"}
          </button>
        </div>

        {lastChecked && (
          <p className="text-xs text-slate-400 mb-4">
            Last checked {lastChecked.toLocaleTimeString()} · {serverCount} server
            {serverCount === 1 ? "" : "s"} scanned · auto-refreshes every 30s
          </p>
        )}

        {scanError && <p className="text-red-600 mb-4">{scanError}</p>}

        {loading && alerts.length === 0 && !scanError && (
          <p className="text-slate-500">Scanning all clients and servers…</p>
        )}

        {!loading && alerts.length === 0 && !scanError && (
          <div className="card p-10 text-center">
            <p className="text-emerald-600 font-medium mb-1">All clear</p>
            <p className="text-sm text-slate-500">
              {healthyCount} process{healthyCount === 1 ? "" : "es"} online across {serverCount}{" "}
              server{serverCount === 1 ? "" : "s"} - nothing needs attention right now.
            </p>
          </div>
        )}

        {serverAlerts.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-slate-600 mb-2">
              Unreachable servers ({serverAlerts.length})
            </h2>
            <div className="space-y-2">
              {serverAlerts.map((a) => (
                <Link
                  key={`srv-${a.serverId}`}
                  href={`/dashboard/${a.clientId}/${a.serverId}`}
                  className="card p-4 flex items-center justify-between border-l-4 border-l-red-400 block hover:shadow-md"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      {a.clientName} · {a.serverName}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{a.detail}</p>
                  </div>
                  <span className="badge bg-red-100 text-red-700 shrink-0 ml-4">unreachable</span>
                </Link>
              ))}
            </div>
          </div>
        )}

        {processAlerts.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-slate-600 mb-2">
              Processes needing attention ({processAlerts.length})
            </h2>
            <div className="space-y-2">
              {processAlerts.map((a) => {
                const isErrored = a.process.status === "errored";
                return (
                  <Link
                    key={`${a.serverId}-${a.process.pm_id}`}
                    href={`/dashboard/${a.clientId}/${a.serverId}`}
                    className={`card p-4 flex items-center justify-between block hover:shadow-md border-l-4 ${
                      isErrored ? "border-l-red-400" : "border-l-amber-400"
                    }`}
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-800">{a.process.name}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {a.clientName} · {a.serverName} · restarts: {a.process.restarts ?? 0}
                      </p>
                    </div>
                    <span
                      className={`badge shrink-0 ml-4 ${
                        isErrored ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {a.process.status}
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
