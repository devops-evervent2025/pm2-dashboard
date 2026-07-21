path = "/var/www/fullstack/pm2-dashboard/frontend/app/dashboard/repos/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add scanningAll state
old_state = "  const [showManage, setShowManage] = useState(false);"
new_state = old_state + "\n  const [scanningAll, setScanningAll] = useState(false);"
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("scanningAll state added")
else:
    print("MISSING: showManage state line")

# 2. Add scanAllRepos function, right after addScanPath/removeScanPath functions
old_remove_fn = '''  async function removeScanPath(id: number) {
    if (!confirm("Remove this scan path? (This only stops scanning it here - nothing is deleted on the server.)")) return;
    await api.delete(`/remote-repos/scan-paths/${id}`);
    await loadAll();
  }'''

new_remove_fn = '''  async function removeScanPath(id: number) {
    if (!confirm("Remove this scan path? (This only stops scanning it here - nothing is deleted on the server.)")) return;
    await api.delete(`/remote-repos/scan-paths/${id}`);
    await loadAll();
  }

  async function scanAllRepos() {
    setScanningAll(true);
    try {
      await api.post("/remote-repos/scan-all");
      await loadAll();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Scan failed");
    } finally {
      setScanningAll(false);
    }
  }'''

if old_remove_fn in content:
    content = content.replace(old_remove_fn, new_remove_fn)
    changes.append("scanAllRepos function added")
else:
    print("MISSING: removeScanPath function")

# 3. Add the button next to "Manage remote scan paths"
old_button = '''          {role === "admin" && (
            <button className="btn-secondary text-xs whitespace-nowrap" onClick={() => setShowManage((v) => !v)}>
              {showManage ? "Hide scan paths" : "Manage remote scan paths"}
            </button>
          )}'''

new_button = '''          {role === "admin" && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                className="btn-primary text-xs whitespace-nowrap"
                onClick={scanAllRepos}
                disabled={scanningAll}
              >
                {scanningAll ? "Scanning…" : "Scan all repos now"}
              </button>
              <button className="btn-secondary text-xs whitespace-nowrap" onClick={() => setShowManage((v) => !v)}>
                {showManage ? "Hide scan paths" : "Manage remote scan paths"}
              </button>
            </div>
          )}'''

if old_button in content:
    content = content.replace(old_button, new_button)
    changes.append("scan-all button added")
else:
    print("MISSING: Manage remote scan paths button block")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
