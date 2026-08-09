"use client";

import { useState } from "react";
import Link from "next/link";
import { DockerContainerItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STATE_STYLES: Record<string, string> = {
  running: "bg-emerald-100 text-emerald-700",
  exited: "bg-slate-200 text-slate-600",
  dead: "bg-red-100 text-red-700",
  restarting: "bg-amber-100 text-amber-700",
  paused: "bg-amber-100 text-amber-700",
  created: "bg-slate-200 text-slate-600",
};

export default function DockerContainerCard({
  serverId,
  clientId,
  container,
  onAction,
}: {
  serverId: number;
  clientId: number;
  container: DockerContainerItem;
  onAction: () => void;
}) {
  const { role } = useAuth();
  const [busy, setBusy] = useState(false);
  const canControl = role === "admin" || role === "developer";

  async function runAction(action: "restart" | "stop" | "start") {
    setBusy(true);
    try {
      await api.post(
        `/servers/${serverId}/containers/${encodeURIComponent(container.name)}/action`,
        { action }
      );
      onAction();
    } catch (err) {
      console.error(err);
    } finally {
      setBusy(false);
    }
  }

  const isRunning = container.state === "running";

  return (
    <div
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800 truncate" title={container.name}>
          {container.name}
        </h4>
        <span
          className={`badge ${STATE_STYLES[container.state] || "bg-slate-100 text-slate-600"}`}
        >
          {container.state}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-y-1 text-xs text-slate-500">
        <span className="truncate" title={container.image}>Image: {container.image}</span>
        <span>Status: {container.status || "-"}</span>
        {container.ports && <span className="truncate" title={container.ports}>Ports: {container.ports}</span>}
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Link
          href={`/dashboard/${clientId}/${serverId}/docker/${encodeURIComponent(container.name)}/logs`}
          className="btn-secondary text-xs"
        >
          View logs
        </Link>

        {canControl && (
          <>
            <button disabled={busy} onClick={() => runAction("restart")} className="btn-secondary text-xs">
              Restart
            </button>
            {isRunning ? (
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
