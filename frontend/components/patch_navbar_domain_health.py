import shutil
from datetime import datetime

path = "Navbar.tsx"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

changes = []

# 1. New interface, placed right after SslNotification
old = '''interface NotificationSummary {
  total: number;
  process_alerts: ProcessNotification[];
  ssl_alerts: SslNotification[];
  generated_at: string;
  cached: boolean;
}'''
new = '''interface DomainDownNotification {
  client_id?: number | null;
  client_name?: string | null;
  server_id: number;
  server_name?: string | null;
  domain: string;
  status_code: number;
  first_detected_at?: string | null;
}

interface NotificationSummary {
  total: number;
  process_alerts: ProcessNotification[];
  ssl_alerts: SslNotification[];
  domain_down_alerts: DomainDownNotification[];
  generated_at: string;
  cached: boolean;
}'''
changes.append((old, new))

# 2. Render block - placed after the ssl_alerts block, before process_alerts,
#    so severity roughly goes: certs expiring -> domains actually down -> processes down
old = '''          {summary && summary.process_alerts.length > 0 && (
            <div className="px-4 py-2 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
                Processes not running
              </p>'''
new = '''          {summary && summary.domain_down_alerts.length > 0 && (
            <div className="px-4 py-2 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
                Domains returning errors
              </p>
              <div className="space-y-1.5">
                {summary.domain_down_alerts.map((a, i) => (
                  <Link
                    key={`domain-${i}`}
                    href="/dashboard/ssl"
                    onClick={() => setOpen(false)}
                    className="block px-2 py-1.5 rounded-md hover:bg-slate-50"
                  >
                    <p className="text-sm text-slate-800">{a.domain}</p>
                    <p className="text-xs text-red-600">
                      HTTP {a.status_code} · {a.client_name || "Unknown client"}
                      {a.server_name ? ` · ${a.server_name}` : ""}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {summary && summary.process_alerts.length > 0 && (
            <div className="px-4 py-2 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">
                Processes not running
              </p>'''
changes.append((old, new))

for old, new in changes:
    count = content.count(old)
    if count != 1:
        print(f"ERROR: expected 1 occurrence, found {count}. Aborting, nothing changed. Block:\\n{old[:120]}...")
        raise SystemExit(1)

for old, new in changes:
    content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)
print("Patched Navbar.tsx successfully.")
