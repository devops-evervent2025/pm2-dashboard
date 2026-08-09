"use client";
import { useState } from "react";
import Link from "next/link";
import { K8sPodItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const PHASE_STYLES: Record<string, string> = {
  Running: "bg-emerald-100 text-emerald-700",
  Pending: "bg-amber-100 text-amber-700",
  Succeeded: "bg-slate-200 text-slate-600",
  Failed: "bg-red-100 text-red-700",
  Unknown: "bg-slate-200 text-slate-600",
  CrashLoopBackOff: "bg-red-100 text-red-700",
};

export default function K8sPodCard({
  clusterId,
  clientId,
  pod,
  onAction,
}: {
  clusterId: number;
  clientId: number;
  pod: K8sPodItem;
  onAction: () => void;
}) {
  const { role } = useAuth();
  const [busy, setBusy] = useState(false);
  // Pod delete is destructive (the controller usually just recreates it,
  // but that's not guaranteed for bare pods) - admin only, stricter than
  // PM2/Docker's admin-or-developer restart/stop.
  const canDelete = role === "admin";

  async function handleDelete() {
    if (!confirm(`Delete pod "${pod.name}"? If it's managed by a Deployment/ReplicaSet it will be recreated automatically.`)) {
      return;
    }
    setBusy(true);
    try {
      await api.post(`/k8s-clusters/${clusterId}/pods/${encodeURIComponent(pod.name)}/action`, {
        namespace: pod.namespace,
        action: "delete",
      });
      onAction();
    } catch (err) {
      console.error(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800 truncate" title={pod.name}>
          {pod.name}
        </h4>
        <span className={`badge ${PHASE_STYLES[pod.phase] || "bg-slate-100 text-slate-600"}`}>
          {pod.phase}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-y-1 text-xs text-slate-500">
        <span>Namespace: {pod.namespace}</span>
        <span>Restarts: {pod.restarts}</span>
        {pod.node_name && <span className="truncate">Node: {pod.node_name}</span>}
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Link
          href={`/dashboard/k8s/${clientId}/${clusterId}/${encodeURIComponent(pod.namespace)}/${encodeURIComponent(pod.name)}/logs`}
          className="btn-secondary text-xs"
        >
          View logs
        </Link>
        {canDelete && (
          <button disabled={busy} onClick={handleDelete} className="btn-secondary text-xs text-red-600">
            Delete pod
          </button>
        )}
      </div>
    </div>
  );
}
