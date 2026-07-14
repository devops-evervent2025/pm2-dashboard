"use client";

import { useState } from "react";
import Link from "next/link";
import { PM2ProcessItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STATUS_STYLES: Record<string, string> = {
  online: "bg-emerald-100 text-emerald-700",
  stopped: "bg-slate-200 text-slate-600",
  errored: "bg-red-100 text-red-700",
  stopping: "bg-amber-100 text-amber-700",
};

function formatUptime(uptimeMs?: number | null) {
  if (!uptimeMs) return "-";
  const seconds = Math.floor((Date.now() - uptimeMs) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function formatMemory(bytes?: number | null) {
  if (!bytes) return "-";
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function ProcessCard({
  serverId,
  clientId,
  process,
  onAction,
}: {
  serverId: number;
  clientId: number;
  process: PM2ProcessItem;
  onAction: () => void;
}) {
  const { role } = useAuth();
  const [busy, setBusy] = useState(false);
  const canControl = role === "admin" || role === "developer";

  async function runAction(action: "restart" | "stop" | "start") {
    setBusy(true);
    try {
      await api.post(`/servers/${serverId}/processes/${process.name}/action`, { action });
      onAction();
    } catch (err) {
      console.error(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800">{process.name}</h4>
        <span className={`badge ${STATUS_STYLES[process.status] || "bg-slate-100 text-slate-600"}`}>
          {process.status}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>PID: {process.pid ?? "-"}</span>
        <span>Restarts: {process.restarts ?? 0}</span>
        <span>CPU: {process.cpu ?? 0}%</span>
        <span>Mem: {formatMemory(process.memory)}</span>
        <span>Uptime: {formatUptime(process.uptime)}</span>
        <span>Mode: {process.exec_mode ?? "-"}</span>
      </div>
      <div className="flex items-center gap-2 pt-1">
        <Link
          href={`/dashboard/${clientId}/${serverId}/${encodeURIComponent(process.name)}/logs`}
          className="btn-secondary text-xs"
        >
          View logs
        </Link>
        {canControl && (
          <>
            <button
              disabled={busy}
              onClick={() => runAction("restart")}
              className="btn-secondary text-xs"
            >
              Restart
            </button>
            {process.status === "online" ? (
              <button disabled={busy} onClick={() => runAction("stop")} className="btn-secondary text-xs">
                Stop
              </button>
            ) : (
              <button disabled={busy} onClick={() => runAction("start")} className="btn-secondary text-xs">
                Start
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
