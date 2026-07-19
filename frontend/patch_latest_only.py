path = "/var/www/fullstack/pm2-dashboard_dev/frontend/app/dashboard/terminal/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old1 = "  const [history, setHistory] = useState<HistoryEntry[]>([]);\n  const [beautified, setBeautified] = useState<Record<string, boolean>>({});"
new1 = "  const [latest, setLatest] = useState<HistoryEntry | null>(null);\n  const [beautified, setBeautified] = useState(false);"
if old1 in content:
    content = content.replace(old1, new1)
    changes.append("state replaced")
else:
    print("MISSING: history+beautified state block")

old2 = '''      const res = await api.post(`/servers/${serverId}/terminal`, { command });
      setHistory((prev) => [
        {
          id: `${Date.now()}`,
          command,
          stdout: res.data.stdout || "",
          stderr: res.data.stderr || "",
          exit_status: res.data.exit_status,
          ranAt,
        },
        ...prev,
      ]);
      setCommand("");
    } catch (err: any) {
      setHistory((prev) => [
        {
          id: `${Date.now()}`,
          command,
          stdout: "",
          stderr: "",
          exit_status: null,
          error: err?.response?.data?.detail || "Command failed.",
          ranAt,
        },
        ...prev,
      ]);
    } finally {'''

new2 = '''      const res = await api.post(`/servers/${serverId}/terminal`, { command });
      setBeautified(false);
      setLatest({
        id: `${Date.now()}`,
        command,
        stdout: res.data.stdout || "",
        stderr: res.data.stderr || "",
        exit_status: res.data.exit_status,
        ranAt,
      });
      setCommand("");
    } catch (err: any) {
      setBeautified(false);
      setLatest({
        id: `${Date.now()}`,
        command,
        stdout: "",
        stderr: "",
        exit_status: null,
        error: err?.response?.data?.detail || "Command failed.",
        ranAt,
      });
    } finally {'''

if old2 in content:
    content = content.replace(old2, new2)
    changes.append("runCommand updated")
else:
    print("MISSING: runCommand try/catch block")

old3 = '''        <div className="space-y-4">
          {history.length === 0 && (
            <p className="text-sm text-slate-400">No commands run yet this session.</p>
          )}
          {history.map((h) => ('''

new3 = '''        <div className="space-y-4">
          {!latest && (
            <p className="text-sm text-slate-400">No command run yet this session.</p>
          )}
          {latest && (() => {
            const h = latest;'''

if old3 in content:
    content = content.replace(old3, new3)
    changes.append("render section header updated")
else:
    print("MISSING: history.map render block start")

# Close the extra IIFE we opened, and fix key references (was h.id-keyed div, now single block)
old4 = '''          ))}
        </div>'''
new4 = '''          })()}
        </div>'''
if old4 in content:
    content = content.replace(old4, new4)
    changes.append("render section footer updated")
else:
    print("MISSING: history.map closing")

old5 = '''            <div key={h.id} className="card p-4">'''
new5 = '''            <div className="card p-4">'''
if old5 in content:
    content = content.replace(old5, new5)
    changes.append("card key removed")
else:
    print("MISSING: card div with key")

old6 = "const isBeautified = !!beautified[h.id];"
new6 = "const isBeautified = beautified;"
if old6 in content:
    content = content.replace(old6, new6)
    changes.append("isBeautified read updated")
else:
    print("MISSING: isBeautified read line")

old7 = '''setBeautified((prev) => ({ ...prev, [h.id]: !prev[h.id] }))'''
new7 = '''setBeautified((prev) => !prev)'''
if old7 in content:
    content = content.replace(old7, new7)
    changes.append("beautify toggle updated")
else:
    print("MISSING: beautify toggle setter")

if len(changes) == 7:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS - all changes applied:", changes)
else:
    print("ABORTED - not all changes matched, file NOT written. Applied so far:", changes)
