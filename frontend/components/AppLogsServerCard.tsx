"use client";

import Link from "next/link";
import { ServerItem } from "@/lib/api";
import EnvBadge from "./EnvBadge";

export default function AppLogsServerCard({ server }: { server: ServerItem }) {
  return (
    <Link
      href={`/dashboard/app-logs/${server.client_id}/${server.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">{server.name}</h3>
        <EnvBadge environment={server.environment} />
      </div>
      <p className="text-sm text-slate-500 font-mono">{server.ip_address}</p>
    </Link>
  );
}
