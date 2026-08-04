"use client";
import { ClientResourceItem } from "@/lib/api";
import ResourceBar from "./ResourceBar";

function statusBadge(status: string) {
  if (status === "online") return "bg-emerald-50 text-emerald-600";
  if (status === "offline") return "bg-red-50 text-red-500";
  return "bg-amber-50 text-amber-600";
}

export default function ClientResourceCard({ data }: { data: ClientResourceItem }) {
  return (
    <div
      data-aos="fade-up"
      data-aos-duration="700"
      data-aos-once="true"
      className="card p-5 flex flex-col gap-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">{data.client_name}</h3>
        <span className="badge bg-brand-50 text-brand-600">
          {data.servers.length} server{data.servers.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="flex flex-col gap-4">
        {data.servers.map((s) => (
          <div key={s.server_id} className="border-t border-slate-100 pt-3 first:border-0 first:pt-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700">{s.name}</span>
              <span className={`badge ${statusBadge(s.status)}`}>{s.status}</span>
            </div>

            {s.status === "online" ? (
              <div className="flex flex-col gap-2">
                <ResourceBar label="CPU" percent={s.cpu_percent} />
                <ResourceBar
                  label="RAM"
                  percent={s.ram_percent}
                  detail={
                    s.ram_used_mb != null && s.ram_total_mb != null
                      ? `${s.ram_used_mb}/${s.ram_total_mb} MB`
                      : undefined
                  }
                />
                <ResourceBar
                  label="Disk"
                  percent={s.disk_percent}
                  detail={
                    s.disk_used && s.disk_total ? `${s.disk_used}/${s.disk_total}` : undefined
                  }
                />
              </div>
            ) : (
              <p className="text-xs text-red-500">{s.error || "Unreachable"}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
