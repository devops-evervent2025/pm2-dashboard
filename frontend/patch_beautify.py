path = "/var/www/fullstack/pm2-dashboard_dev/frontend/app/dashboard/terminal/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add a helper function to try pretty-printing JSON, right before the component
old_marker = "export default function ServerTerminalPage() {"
helper = '''function tryPrettyPrint(text: string): { pretty: string | null; isJson: boolean } {
  const trimmed = text.trim();
  if (!trimmed) return { pretty: null, isJson: false };
  try {
    const parsed = JSON.parse(trimmed);
    return { pretty: JSON.stringify(parsed, null, 2), isJson: true };
  } catch {
    return { pretty: null, isJson: false };
  }
}

export default function ServerTerminalPage() {'''
if old_marker in content:
    content = content.replace(old_marker, helper)
    changes.append("helper added")
else:
    print("MISSING: component start marker")

# 2. Add beautify state alongside history state
old_state = "  const [history, setHistory] = useState<HistoryEntry[]>([]);"
new_state = old_state + "\n  const [beautified, setBeautified] = useState<Record<string, boolean>>({});"
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("state added")
else:
    print("MISSING: history state line")

# 3. Replace the stdout <pre> block with a version that has a Beautify toggle
old_stdout_block = '''              {h.stdout && (
                <pre className="bg-slate-950 text-green-300 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap mb-2">
                  {h.stdout}
                </pre>
              )}'''

new_stdout_block = '''              {h.stdout && (() => {
                const { pretty, isJson } = tryPrettyPrint(h.stdout);
                const isBeautified = !!beautified[h.id];
                const displayText = isJson && isBeautified && pretty ? pretty : h.stdout;
                return (
                  <div className="mb-2">
                    {isJson && (
                      <div className="flex justify-end mb-1">
                        <button
                          onClick={() =>
                            setBeautified((prev) => ({ ...prev, [h.id]: !prev[h.id] }))
                          }
                          className="text-xs px-2 py-1 rounded-md bg-slate-700 text-slate-100 hover:bg-slate-600"
                        >
                          {isBeautified ? "Show raw" : "Beautify"}
                        </button>
                      </div>
                    )}
                    <pre className="bg-slate-950 text-green-300 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap">
                      {displayText}
                    </pre>
                  </div>
                );
              })()}'''

if old_stdout_block in content:
    content = content.replace(old_stdout_block, new_stdout_block)
    changes.append("stdout block wrapped with beautify toggle")
else:
    print("MISSING: stdout <pre> block (exact match failed)")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS - all changes applied:", changes)
else:
    print("ABORTED - not all changes matched, file NOT written. Applied so far:", changes)
