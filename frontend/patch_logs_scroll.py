path = "/var/www/fullstack/pm2-dashboard_dev/frontend/components/LogsTerminal.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add isAtBottom state, right after isFullscreen state
old_state = '  const [isFullscreen, setIsFullscreen] = useState(false);'
new_state = '''  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);'''
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("isAtBottom state added")
else:
    print("MISSING: isFullscreen state line")

# 2. Replace the unconditional auto-scroll effect with a conditional one,
#    and add a scroll handler that tracks whether the user is near the bottom.
old_scroll_effect = '''  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [lines]);'''

new_scroll_effect = '''  // Only auto-scroll to the newest lines if the user is already near the
  // bottom - if they've scrolled up to read earlier output, new incoming
  // lines must NOT yank them back down.
  useEffect(() => {
    if (!isAtBottom) return;
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [lines, isAtBottom]);

  const BOTTOM_THRESHOLD_PX = 60;

  function handleScroll() {
    const el = containerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsAtBottom(distanceFromBottom <= BOTTOM_THRESHOLD_PX);
  }

  function jumpToLatest() {
    setIsAtBottom(true);
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: "smooth" });
  }'''

if old_scroll_effect in content:
    content = content.replace(old_scroll_effect, new_scroll_effect)
    changes.append("scroll effect + handler replaced")
else:
    print("MISSING: old scroll effect")

# 3. Wire onScroll onto the scrollable container, and add "Jump to latest" button + wrap the log area in a relative container
old_container = '''      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto bg-slate-900 text-slate-100 font-mono text-xs p-4 space-y-0.5"
      >
        {lines.length === 0 && (
          <p className="text-slate-500">Waiting for log output…</p>
        )}
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all">
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}'''

new_container = '''      <div className="relative flex-1 min-h-0">
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto bg-slate-900 text-slate-100 font-mono text-xs p-4 space-y-0.5"
        >
          {lines.length === 0 && (
            <p className="text-slate-500">Waiting for log output…</p>
          )}
          {lines.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap break-all">
              {line}
            </div>
          ))}
        </div>
        {!isAtBottom && (
          <button
            type="button"
            onClick={jumpToLatest}
            className="absolute bottom-3 right-3 px-3 py-1.5 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-100 text-xs font-medium shadow-lg flex items-center gap-1"
          >
            ↓ Jump to latest
          </button>
        )}
      </div>
    </div>
  );
}'''

if old_container in content:
    content = content.replace(old_container, new_container)
    changes.append("scroll container + jump-to-latest button added")
else:
    print("MISSING: log container block")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
