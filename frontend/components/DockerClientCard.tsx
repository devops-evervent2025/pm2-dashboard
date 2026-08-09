"use client";
import Link from "next/link";
import { ClientItem } from "@/lib/api";

export default function DockerClientCard({ client }: { client: ClientItem }) {
  return (
    <Link
      href={`/dashboard/docker/${client.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <h3 className="font-semibold text-slate-800">{client.name}</h3>
      {client.description && (
        <p className="text-sm text-slate-500">{client.description}</p>
      )}
      <p className="text-xs text-slate-400">
        {client.server_count} server{client.server_count === 1 ? "" : "s"}
      </p>
    </Link>
  );
}
