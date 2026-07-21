"use client";

import Link from "next/link";
import { useState } from "react";
import { ServerItem, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import EnvBadge from "./EnvBadge";

export default function ServerCard({
  server,
  onDeleted,
}: {
  server: ServerItem;
  onDeleted?: () => void;
}) {
  const { role } = useAuth();
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (
      !confirm(
        `Delete server "${server.name}" (${server.ip_address})? This cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(true);

    try {
      await api.delete(`/servers/${server.id}`);
      onDeleted?.();
    } catch (err: any) {
      console.error(err);
      alert(err?.response?.data?.detail || "Failed to delete server.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Link
      href={`/dashboard/${server.client_id}/${server.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">
          {server.name}
        </h3>

        <EnvBadge environment={server.environment} />
      </div>

      <p className="text-sm text-slate-500 font-mono">
        {server.ip_address}
      </p>

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              server.online === undefined || server.online === null
                ? "bg-slate-300"
                : server.online
                ? "bg-emerald-500"
                : "bg-red-500"
            }`}
          />

          {server.online === undefined || server.online === null
            ? "Status unknown"
            : server.online
            ? "Online"
            : "Unreachable"}

          <span>
            · {server.ssh_username}@{server.ip_address}:{server.ssh_port}
          </span>
        </span>

        {role === "admin" && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
        )}
      </div>
    </Link>
  );
}
