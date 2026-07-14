const STYLES: Record<string, string> = {
  Dev: "bg-blue-100 text-blue-700",
  Prod: "bg-red-100 text-red-700",
  Stg: "bg-amber-100 text-amber-700",
  Other: "bg-slate-100 text-slate-600",
};

export default function EnvBadge({ environment }: { environment: string }) {
  return <span className={`badge ${STYLES[environment] || STYLES.Other}`}>{environment}</span>;
}
