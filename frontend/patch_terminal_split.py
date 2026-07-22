path = "/var/www/fullstack/pm2-dashboard_dev/frontend/app/dashboard/terminal/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add imports for LogsTerminal + PM2ProcessItem type
old_import = 'import { api, ServerItem } from "@/lib/api";'
new_import = '''import { api, ServerItem, PM2ProcessItem } from "@/lib/api";
import LogsTerminal from "@/components/LogsTerminal";'''
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("imports added")
else:
    print("MISSING: api import line")

# 2. Add process list state + fetching, right after loadServers effect
old_state_block = '''  const loadServers = useCallback(async () => {
    try {
      const res = await api.get<ServerItem[]>("/servers");
      setServers(res.data);
    } catch {
      setLoadError("Could not load servers.");
    }
  }, []);

  useEffect(() => {
    if (role) loadServers();
  }, [role, loadServers]);'''

new_state_block = '''  const [processes, setProcesses] = useState<PM2ProcessItem[]>([]);
  const [selectedProcess, setSelectedProcess] = useState<string>("");
  const [loadingProcesses, setLoadingProcesses] = useState(false);
  const [processError, setProcessError] = useState("");

  const loadServers = useCallback(async () => {
    try {
      const res = await api.get<ServerItem[]>("/servers");
      setServers(res.data);
    } catch {
      setLoadError("Could not load servers.");
    }
  }, []);

  useEffect(() => {
    if (role) loadServers();
  }, [role, loadServers]);

  useEffect(() => {
    setSelectedProcess("");
    setProcesses([]);
    setProcessError("");
    if (!serverId) return;
    setLoadingProcesses(true);
    api
      .get<PM2ProcessItem[]>(`/servers/${serverId}/processes`)
      .then((res) => setProcesses(res.data))
      .catch(() => setProcessError("Could not load processes for this server."))
      .finally(() => setLoadingProcesses(false));
  }, [serverId]);'''

if old_state_block in content:
    content = content.replace(old_state_block, new_state_block)
    changes.append("process list state + fetch effect added")
else:
    print("MISSING: loadServers block")

# 3. Wrap the whole page body in a two-column grid: left = existing curl UI, right = process-picker + LogsTerminal
old_main_open = '''      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">Server Terminal</h1>
        <p className="text-sm text-slate-500 mb-6">
          Run curl commands against a managed server over its existing SSH connection.
          Only plain curl commands are allowed - no downloading files, and no commands
          copied from a browser's "Copy as cURL" (those carry session cookies).
          Every command run here is logged.
        </p>

        <div className="card p-6 mb-6">'''

new_main_open = '''      <main className="max-w-[100rem] mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">Server Terminal</h1>
        <p className="text-sm text-slate-500 mb-6">
          Run curl commands against a managed server over its existing SSH connection.
          Only plain curl commands are allowed - no downloading files, and no commands
          copied from a browser's "Copy as cURL" (those carry session cookies).
          Every command run here is logged.
        </p>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        <div>

        <div className="card p-6 mb-6">'''

if old_main_open in content:
    content = content.replace(old_main_open, new_main_open)
    changes.append("left column opened")
else:
    print("MISSING: main open block")

# 4. Close the left column right after the command-history section, open the right column with process-picker + LogsTerminal
old_history_end = '''            );
          })()}
        </div>
      </main>
    </div>
  );
}'''

new_history_end = '''            );
          })()}
        </div>
        </div>

        <div>
          <div className="card p-6 mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-1">Process (live logs)</label>
            <select
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value)}
              disabled={!serverId || loadingProcesses}
            >
              <option value="">
                {!serverId
                  ? "Select a server first…"
                  : loadingProcesses
                  ? "Loading processes…"
                  : "Select a process…"}
              </option>
              {processes.map((p) => (
                <option key={p.pm_id} value={p.name}>
                  {p.name} ({p.status})
                </option>
              ))}
            </select>
            {processError && <p className="text-xs text-red-600 mt-2">{processError}</p>}
          </div>

          {serverId && selectedProcess ? (
            <LogsTerminal serverId={Number(serverId)} processName={selectedProcess} />
          ) : (
            <div className="card p-10 text-center text-slate-400 text-sm">
              Select a server and a process above to stream its live logs here.
            </div>
          )}
        </div>
        </div>
      </main>
    </div>
  );
}'''

if old_history_end in content:
    content = content.replace(old_history_end, new_history_end)
    changes.append("right column with process-picker + LogsTerminal added")
else:
    print("MISSING: history-section end block")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
