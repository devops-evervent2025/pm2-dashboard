"use client";
import Link from "next/link";
import { ServerItem } from "@/lib/api";
import EnvBadge from "./EnvBadge";

export default function DockerServerCard({ server }: { server: ServerItem }) {
  return (
    <Link
      href={`/dashboard/docker/${server.client_id}/${server.id}`}
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
      <div className="flex items-center text-xs text-slate-400">
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
      </div>
    </Link>
  );
}
