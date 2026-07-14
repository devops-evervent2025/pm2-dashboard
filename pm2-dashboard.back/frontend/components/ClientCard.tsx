"use client";

import Link from "next/link";
import { ClientItem } from "@/lib/api";

export default function ClientCard({ client }: { client: ClientItem }) {
  return (
    <Link href={`/dashboard/${client.id}`} className="card p-5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">{client.name}</h3>
        <span className="badge bg-brand-50 text-brand-600">
          {client.server_count} server{client.server_count === 1 ? "" : "s"}
        </span>
      </div>
      {client.description && (
        <p className="text-sm text-slate-500 line-clamp-2">{client.description}</p>
      )}
      <span className="text-xs text-slate-400 mt-1">
        Added {new Date(client.created_at).toLocaleDateString()}
      </span>
    </Link>
  );
}
