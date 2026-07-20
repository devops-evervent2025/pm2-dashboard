path = "/var/www/fullstack/pm2-dashboard/frontend/app/dashboard/repos/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add searchQuery state, right after openGroup state
old_state = '''  const [openGroup, setOpenGroup] = useState<string | null>(null);'''
new_state = '''  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");'''
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("searchQuery state added")
else:
    print("MISSING: openGroup state line")

# 2. Add the search input box, right before the grid that holds the repo list
old_grid_start = '''        {error && <p className="text-red-600 mb-4">{error}</p>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <div className="card divide-y divide-slate-100 overflow-hidden">'''
new_grid_start = '''        {error && <p className="text-red-600 mb-4">{error}</p>}

        <div className="mb-4">
          <input
            type="text"
            placeholder="Search by client/server name or repo name…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field text-sm w-full max-w-md"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <div className="card divide-y divide-slate-100 overflow-hidden">'''
if old_grid_start in content:
    content = content.replace(old_grid_start, new_grid_start)
    changes.append("search input box added")
else:
    print("MISSING: grid start block")

# 3. Filter unifiedRepos by search query BEFORE grouping (matches group label OR repo name),
#    and auto-open the matching group(s) while searching so results aren't hidden behind
#    a collapsed accordion.
old_grouping = '''              {!loadingRepos &&
                Object.entries(
                  unifiedRepos.reduce<Record<string, UnifiedRepo[]>>((acc, r) => {
                    const label = groupLabel(r.source);
                    (acc[label] = acc[label] || []).push(r);
                    return acc;
                  }, {})
                ).map(([label, repos]) => {
                  const isCollapsed = openGroup !== label;
                  return ('''

new_grouping = '''              {!loadingRepos &&
                (() => {
                  const q = searchQuery.trim().toLowerCase();
                  const filtered = q
                    ? unifiedRepos.filter(
                        (r) =>
                          groupLabel(r.source).toLowerCase().includes(q) ||
                          r.name.toLowerCase().includes(q)
                      )
                    : unifiedRepos;

                  const grouped = Object.entries(
                    filtered.reduce<Record<string, UnifiedRepo[]>>((acc, r) => {
                      const label = groupLabel(r.source);
                      (acc[label] = acc[label] || []).push(r);
                      return acc;
                    }, {})
                  );

                  if (q && grouped.length === 0) {
                    return (
                      <p className="p-4 text-sm text-slate-500">
                        No clients, servers, or repos match &quot;{searchQuery}&quot;.
                      </p>
                    );
                  }

                  return grouped.map(([label, repos]) => {
                    const isCollapsed = q ? false : openGroup !== label;
                    return (''';

if old_grouping in content:
    content = content.replace(old_grouping, new_grouping)
    changes.append("grouping replaced with search-filtered version")
else:
    print("MISSING: grouping reduce block")

# 4. Close the extra wrapping we introduced (the outer IIFE + arrow function from .map)
old_close = '''                        ))}
                    </div>
                  );
                })}
            </div>
          </div>'''

new_close = '''                        ))}
                    </div>
                    );
                  });
                })()}
            </div>
          </div>'''

if old_close in content:
    content = content.replace(old_close, new_close)
    changes.append("closing braces balanced")
else:
    print("MISSING: grouping .map closing block")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
