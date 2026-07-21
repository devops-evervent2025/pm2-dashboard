path = "/var/www/fullstack/pm2-dashboard_dev/frontend/app/dashboard/repos/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Update ScanPath interface + UnifiedRepo source type to carry client info
old_iface = '''interface ScanPath {
  id: number;
  server_id: number;
  server_name?: string | null;
  base_path: string;
  label?: string | null;
}'''
new_iface = '''interface ScanPath {
  id: number;
  server_id: number;
  server_name?: string | null;
  client_id?: number | null;
  client_name?: string | null;
  base_path: string;
  label?: string | null;
}'''
if old_iface in content:
    content = content.replace(old_iface, new_iface)
    changes.append("ScanPath interface updated")
else:
    print("MISSING: ScanPath interface")

old_source_type = '''  source: "local" | { scanPathId: number; serverName: string; basePath: string; label?: string | null };'''
new_source_type = '''  source: "local" | { scanPathId: number; serverName: string; basePath: string; label?: string | null; clientId?: number | null; clientName?: string | null };'''
if old_source_type in content:
    content = content.replace(old_source_type, new_source_type)
    changes.append("UnifiedRepo source type updated")
else:
    print("MISSING: UnifiedRepo source type")

old_push = '''            source: {
              scanPathId: sp.id,
              serverName: sp.server_name || `Server #${sp.server_id}`,
              basePath: sp.base_path,
              label: sp.label,
            },'''
new_push = '''            source: {
              scanPathId: sp.id,
              serverName: sp.server_name || `Server #${sp.server_id}`,
              basePath: sp.base_path,
              label: sp.label,
              clientId: sp.client_id ?? null,
              clientName: sp.client_name ?? null,
            },'''
if old_push in content:
    content = content.replace(old_push, new_push)
    changes.append("push into items updated")
else:
    print("MISSING: source push block")

# 2. Add selectedClientKey state (null = client-list view, "local" or a client_id = detail view)
old_state = '''  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");'''
new_state = '''  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedClientKey, setSelectedClientKey] = useState<string | null>(null);'''
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("selectedClientKey state added")
else:
    print("MISSING: openGroup+searchQuery state block")

# 3. Add a clientKey helper right after groupLabel
old_grouplabel_fn = '''  function groupLabel(source: UnifiedRepo["source"]): string {
    if (source === "local") return "Local (this server)";
    if (source.label) return `${source.serverName} · ${source.label}`;
    return `${source.serverName} · ${source.basePath}`;
  }'''
new_grouplabel_fn = '''  function groupLabel(source: UnifiedRepo["source"]): string {
    if (source === "local") return "Local (this server)";
    if (source.label) return `${source.serverName} · ${source.label}`;
    return `${source.serverName} · ${source.basePath}`;
  }

  function clientKey(source: UnifiedRepo["source"]): string {
    if (source === "local") return "local";
    if (source.clientId != null) return `client-${source.clientId}`;
    return "unassigned";
  }

  function clientDisplayName(source: UnifiedRepo["source"]): string {
    if (source === "local") return "Local (this server)";
    if (source.clientName) return source.clientName;
    return "Unassigned / Unknown client";
  }'''
if old_grouplabel_fn in content:
    content = content.replace(old_grouplabel_fn, new_grouplabel_fn)
    changes.append("clientKey/clientDisplayName helpers added")
else:
    print("MISSING: groupLabel function")

if len(changes) == 5:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
