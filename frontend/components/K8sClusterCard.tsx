"use client";
import Link from "next/link";
import { useState } from "react";
import { K8sClusterItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import EditClusterModal from "@/components/EditClusterModal";

const CONN_LABELS: Record<string, string> = {
  ssh_kubectl: "SSH + kubectl",
  kubeconfig: "Kubeconfig",
  api_token: "API + Token",
};

export default function K8sClusterCard({
  cluster,
  onDeleted,
  onUpdated,
}: {
  cluster: K8sClusterItem;
  onDeleted?: () => void;
  onUpdated?: () => void;
}) {
  const { role } = useAuth();
  const [deleting, setDeleting] = useState(false);
  const [showEdit, setShowEdit] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Delete cluster "${cluster.name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await api.delete(`/k8s-clusters/${cluster.id}`);
      onDeleted?.();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to delete cluster.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
    <Link
      href={`/dashboard/k8s/${cluster.client_id}/${cluster.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">{cluster.name}</h3>
        {cluster.environment && (
          <span className="badge bg-brand-50 text-brand-600">{cluster.environment}</span>
        )}
      </div>
      <p className="text-xs text-slate-400">{CONN_LABELS[cluster.connection_type]}</p>
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              cluster.online === undefined || cluster.online === null
                ? "bg-slate-300"
                : cluster.online
                ? "bg-emerald-500"
                : "bg-red-500"
            }`}
          />
          {cluster.online === undefined || cluster.online === null
            ? "Status unknown"
            : cluster.online
            ? "Online"
            : "Unreachable"}
        </span>
        {role === "admin" && (
          <div className="flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowEdit(true);
              }}
              className="text-slate-500 hover:text-slate-800"
            >
              Edit
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-red-500 hover:text-red-700"
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        )}
      </div>
    </Link>
      {showEdit && (
        <EditClusterModal
          clusterId={cluster.id}
          onClose={() => setShowEdit(false)}
          onUpdated={() => onUpdated?.()}
        />
      )}
    </>
  );
}
