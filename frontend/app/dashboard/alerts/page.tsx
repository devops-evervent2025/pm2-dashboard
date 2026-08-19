"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ClientItem, ServerItem, PM2ProcessItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

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

  // ---- Alert check interval settings (admin only) ----
  interface AlertSetting {
    alert_type: string;
    label: string;
    interval_minutes: number;
  }
  const [alertSettings, setAlertSettings] = useState<AlertSetting[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [savingType, setSavingType] = useState<string | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState<string | null>(null);

  const loadAlertSettings = useCallback(async () => {
    if (role !== "admin") return;
    setSettingsLoading(true);
    setSettingsError(null);
    try {
      const res = await api.get<AlertSetting[]>("/alert-settings");
      setAlertSettings(res.data);
    } catch (err: any) {
      setSettingsError(err?.response?.data?.detail || "Could not load alert settings.");
    } finally {
      setSettingsLoading(false);
    }
  }, [role]);

  useEffect(() => {
    if (role === "admin") loadAlertSettings();
  }, [role, loadAlertSettings]);

  const updateLocalInterval = (alertType: string, minutes: number) => {
    setAlertSettings((prev) =>
      prev.map((s) => (s.alert_type === alertType ? { ...s, interval_minutes: minutes } : s))
    );
  };

  const saveInterval = async (alertType: string, minutes: number) => {
    if (!minutes || minutes < 1) return;
    setSavingType(alertType);
    setSettingsError(null);
    try {
      await api.put(`/alert-settings/${alertType}`, { interval_minutes: minutes });
      setSavedFlash(alertType);
      setTimeout(() => setSavedFlash((prev) => (prev === alertType ? null : prev)), 1500);
    } catch (err: any) {
      setSettingsError(err?.response?.data?.detail || "Could not save this interval.");
    } finally {
      setSavingType(null);
    }
  };

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
    // Alerts is admin-only. A non-admin who reaches this page directly
    // by URL (not via the sidebar, which already hides this link for
    // them) gets bounced to the dashboard instead of seeing the page -
    // hiding the sidebar link alone is cosmetic, not access control.
    if (!isLoading && role && role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    if (role === "admin") runScan();
  }, [role, isLoading, router, runScan]);

  useEffect(() => {
    if (!role) return;
    const interval = setInterval(runScan, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [role, runScan]);

  const processAlerts = alerts.filter((a): a is ProcessAlert => a.type === "process");
  const serverAlerts = alerts.filter((a): a is ServerAlert => a.type === "server_unreachable");

  // Don't flash the admin-only content while the redirect above is
  // still in flight, or for a non-admin who briefly has a stale role.
  if (isLoading || !role || role !== "admin") {
    return (
      <div className="flex flex-col h-full min-h-0">
        <Navbar crumbs={[{ label: "Alerts" }]} />
        <div className="relative flex-1 overflow-y-auto min-h-0">
          <PageLoadingOverlay show message="Loading alerts" subMessage="Verifying admin access" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <Navbar crumbs={[{ label: "Alerts" }]} />
      <div className="relative flex-1 overflow-y-auto min-h-0">
        <PageLoadingOverlay
          show={loading && alerts.length === 0 && !scanError}
          message="Scanning alerts"
          subMessage="Checking all clients and servers via SSH"
        />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Alerts</h1>
            <p className="text-sm text-slate-500">
              Any PM2 process that isn&apos;t <span className="font-mono">online</span>, or any
              server we couldn&apos;t reach, shows up here across all clients.
            </p>
          </div>
          <button className="btn-secondary text-sm inline-flex items-center gap-1.5" onClick={runScan} disabled={loading}>
            {loading ? (<><Spinner size="xs" /><span>Scanning</span></>) : "Refresh"}
          </button>
        </div>

        {role === "admin" && (
          <div className="card mb-6 overflow-hidden">
            <button
              type="button"
              onClick={() => setSettingsOpen((prev) => !prev)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="w-4 h-4 text-slate-400"
                >
                  <path
                    fillRule="evenodd"
                    d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="text-sm font-medium text-slate-700">Alert Check Intervals</span>
              </div>
              <svg
                className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${settingsOpen ? "rotate-180" : ""}`}
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                  clipRule="evenodd"
                />
              </svg>
            </button>

            <div
              className="transition-all duration-300 ease-in-out overflow-hidden"
              style={{ maxHeight: settingsOpen ? "600px" : "0px" }}
            >
              <div className="px-4 pb-4 pt-1 border-t border-slate-100">
                <p className="text-xs text-slate-500 mb-3">
                  How often each background scanner checks for problems and emails alerts. Changes apply on the next cycle - no restart needed.
                </p>

                {settingsError && <p className="text-sm text-red-600 mb-3">{settingsError}</p>}

                {settingsLoading ? (
                  <LoadingState message="Loading" variant="compact" />
                ) : (
                  <div className="space-y-2">
                    {alertSettings.map((s) => (
                      <div
                        key={s.alert_type}
                        className="flex items-center justify-between gap-3 py-2 border-b border-slate-50 last:border-b-0"
                      >
                        <span className="text-sm text-slate-700">{s.label}</span>
                        <div className="flex items-center gap-2 shrink-0">
                          <input
                            type="number"
                            min={1}
                            max={10080}
                            value={s.interval_minutes}
                            onChange={(e) => updateLocalInterval(s.alert_type, Number(e.target.value))}
                            className="w-20 border border-slate-300 rounded-md px-2 py-1 text-sm text-right"
                          />
                          <span className="text-xs text-slate-400 w-10">min</span>
                          <button
                            onClick={() => saveInterval(s.alert_type, s.interval_minutes)}
                            disabled={savingType === s.alert_type}
                            className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${
                              savedFlash === s.alert_type
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                            } disabled:opacity-50`}
                          >
                            {savingType === s.alert_type ? "Saving…" : savedFlash === s.alert_type ? "Saved ✓" : "Save"}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {lastChecked && (
          <p className="text-xs text-slate-400 mb-4">
            Last checked {lastChecked.toLocaleTimeString()} · {serverCount} server
            {serverCount === 1 ? "" : "s"} scanned · auto-refreshes every 30s
          </p>
        )}

        {scanError && <p className="text-red-600 mb-4">{scanError}</p>}

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
		  data-aos="fade-up"
  		  data-aos-duration="700"
  		  data-aos-once="true"
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
    </div>
  );
}
