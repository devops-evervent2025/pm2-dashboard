path = "/var/www/fullstack/pm2-dashboard_dev/frontend/components/LogsTerminal.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add a helper right before the component definition that figures out
#    a color class for a given log line - tries to parse JSON "level"
#    first (matches this app's structured logs), falls back to plain
#    keyword matching for non-JSON lines.
old_marker = "export default function LogsTerminal({"
helper = '''function logLineColorClass(line: string): string {
  // Structured JSON logs (this app's backend format) carry an explicit
  // "level" field - trust that over guessing from keywords when present.
  const jsonMatch = line.match(/"level"\\s*:\\s*"([a-zA-Z]+)"/);
  const level = jsonMatch ? jsonMatch[1].toLowerCase() : null;

  if (level === "error" || level === "fatal" || level === "critical") {
    return "text-red-400";
  }
  if (level === "warn" || level === "warning") {
    return "text-amber-400";
  }
  if (level === "info" || level === "success") {
    return "text-emerald-400";
  }

  // No structured level found - fall back to keyword sniffing so plain
  // (non-JSON) log lines still get colored sensibly.
  const lowered = line.toLowerCase();
  if (/\\berror\\b|\\bfatal\\b|\\bexception\\b|\\bfailed\\b/.test(lowered)) {
    return "text-red-400";
  }
  if (/\\bwarn(ing)?\\b/.test(lowered)) {
    return "text-amber-400";
  }
  if (/\\bsuccess(ful(ly)?)?\\b/.test(lowered)) {
    return "text-emerald-400";
  }
  return "text-slate-100";
}


''' + old_marker

if old_marker in content and "logLineColorClass" not in content:
    content = content.replace(old_marker, helper)
    changes.append("logLineColorClass helper added")
else:
    print("MISSING or already present: component definition marker")

# 2. Apply the color class to each rendered line
old_render = '''        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all">
            {line}
          </div>
        ))}'''

new_render = '''        {lines.map((line, i) => (
          <div key={i} className={`whitespace-pre-wrap break-all ${logLineColorClass(line)}`}>
            {line}
          </div>
        ))}'''

if old_render in content:
    content = content.replace(old_render, new_render)
    changes.append("line rendering updated with color class")
else:
    print("MISSING: line rendering block")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
