"use client";

import Link from "next/link";
import { useState } from "react";
import { ClientItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ClientCard({
  client,
  onDeleted,
}: {
  client: ClientItem;
  onDeleted?: () => void;
}) {
  const { role } = useAuth();
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (
      !confirm(
        `Delete client "${client.name}"? This will also delete all ${client.server_count} of its server(s). This cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(true);

    try {
      await api.delete(`/clients/${client.id}`);
      onDeleted?.();
    } catch (err: any) {
      console.error(err);
      alert(err?.response?.data?.detail || "Failed to delete client.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Link
      href={`/dashboard/${client.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">
          {client.name}
        </h3>

        <span className="badge bg-brand-50 text-brand-600">
          {client.server_count} server
          {client.server_count === 1 ? "" : "s"}
        </span>
      </div>

      {client.description && (
        <p className="text-sm text-slate-500 line-clamp-2">
          {client.description}
        </p>
      )}

      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-slate-400">
          Added {new Date(client.created_at).toLocaleDateString()}
        </span>

        {role === "admin" && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="text-xs text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
        )}
      </div>
    </Link>
  );
}
