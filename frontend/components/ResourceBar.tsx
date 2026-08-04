"use client";

function colorFor(pct: number | null | undefined) {
  if (pct == null) return "bg-slate-300";
  if (pct < 60) return "bg-emerald-500";
  if (pct < 85) return "bg-amber-500";
  return "bg-red-500";
}

export default function ResourceBar({
  label,
  percent,
  detail,
}: {
  label: string;
  percent: number | null | undefined;
  detail?: string;
}) {
  const pct = percent == null ? 0 : Math.min(100, Math.max(0, percent));
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">{label}</span>
        <span className="text-slate-600 font-medium">
          {percent == null ? "—" : `${percent}%`}
          {detail ? <span className="text-slate-400 font-normal"> · {detail}</span> : null}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colorFor(percent)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
