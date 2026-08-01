"use client";

import Link from "next/link";
import { ClientItem } from "@/lib/api";

export default function AppLogsClientCard({ client }: { client: ClientItem }) {
  return (
    <Link
      href={`/dashboard/app-logs/${client.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">{client.name}</h3>
        <span className="badge bg-brand-50 text-brand-600">
          {client.server_count} server{client.server_count === 1 ? "" : "s"}
        </span>
      </div>
      <span className="text-xs text-slate-400">
        Added {new Date(client.created_at).toLocaleDateString()}
      </span>
    </Link>
  );
}
