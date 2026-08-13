"use client";
import Link from "next/link";
import { useState } from "react";
import { K8sClientItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import EditK8sClientModal from "@/components/EditK8sClientModal";

export default function K8sClientCard({
  client,
  onDeleted,
  onUpdated,
}: {
  client: K8sClientItem;
  onDeleted?: () => void;
  onUpdated?: () => void;
}) {
  const { role } = useAuth();
  const [deleting, setDeleting] = useState(false);
  const [showEdit, setShowEdit] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (
      !confirm(
        `Delete client "${client.name}"? This will also delete all ${client.cluster_count} of its cluster(s). This cannot be undone.`
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await api.delete(`/k8s-clients/${client.id}`);
      onDeleted?.();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to delete client.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Link
      href={`/dashboard/k8s/${client.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">{client.name}</h3>
        <span className="badge bg-brand-50 text-brand-600">
          {client.cluster_count} cluster{client.cluster_count === 1 ? "" : "s"}
        </span>
      </div>
      {client.description && (
        <p className="text-sm text-slate-500 line-clamp-2">{client.description}</p>
      )}
      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-slate-400">
          Added {new Date(client.created_at).toLocaleDateString()}
        </span>
        {role === "admin" && (
          <div className="flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowEdit(true);
              }}
              className="text-xs text-slate-500 hover:text-slate-800"
            >
              Edit
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-xs text-red-500 hover:text-red-700"
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        )}
      </div>
      {showEdit && (
        <EditK8sClientModal
          client={client}
          onClose={() => setShowEdit(false)}
          onUpdated={() => onUpdated?.()}
        />
      )}
    </Link>
  );
}
