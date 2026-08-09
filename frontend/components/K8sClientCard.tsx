"use client";
import Link from "next/link";
import { ClientItem } from "@/lib/api";

export default function K8sClientCard({ client }: { client: ClientItem }) {
  return (
    <Link
      href={`/dashboard/k8s/${client.id}`}
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-2 group"
    >
      <h3 className="font-semibold text-slate-800">{client.name}</h3>
      {client.description && (
        <p className="text-sm text-slate-500 line-clamp-2">{client.description}</p>
      )}
      <span className="text-xs text-slate-400">
        Added {new Date(client.created_at).toLocaleDateString()}
      </span>
    </Link>
  );
}
