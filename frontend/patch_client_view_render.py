path = "/var/www/fullstack/pm2-dashboard_dev/frontend/app/dashboard/repos/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# Replace the search box + grid section start with: search box + client-list-view OR detail-view wrapper
old_block = '''        <div className="mb-4">
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

new_block = '''        <div className="mb-4">
          <input
            type="text"
            placeholder="Search by client/server name or repo name…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field text-sm w-full max-w-md"
          />
        </div>

        {!loadingRepos && !selectedClientKey && (() => {
          const q = searchQuery.trim().toLowerCase();
          const clientMap = new Map<string, { name: string; repoCount: number }>();
          for (const r of unifiedRepos) {
            const key = clientKey(r.source);
            const name = clientDisplayName(r.source);
            if (q && !name.toLowerCase().includes(key === "local" ? "local" : name.toLowerCase()) && !name.toLowerCase().includes(q)) continue;
            const existing = clientMap.get(key);
            if (existing) {
              existing.repoCount += 1;
            } else {
              clientMap.set(key, { name, repoCount: 1 });
            }
          }
          const clientCards = Array.from(clientMap.entries()).sort((a, b) => {
            if (a[0] === "local") return -1;
            if (b[0] === "local") return 1;
            return a[1].name.localeCompare(b[1].name);
          });

          if (clientCards.length === 0) {
            return <p className="text-sm text-slate-500">No clients match your search.</p>;
          }

          return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {clientCards.map(([key, info]) => (
                <button
                  key={key}
                  onClick={() => setSelectedClientKey(key)}
                  className="card p-5 text-left hover:shadow-md transition-shadow"
                >
                  <h3 className="text-base font-semibold text-slate-800">{info.name}</h3>
                  <p className="text-sm text-slate-500 mt-1">{info.repoCount} repo(s)</p>
                </button>
              ))}
            </div>
          );
        })()}

        {!loadingRepos && selectedClientKey && (
          <button
            onClick={() => setSelectedClientKey(null)}
            className="text-sm text-brand-600 hover:text-brand-800 mb-4 flex items-center gap-1"
          >
            ← Back to all clients
          </button>
        )}

        {(loadingRepos || selectedClientKey) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1">
            <div className="card divide-y divide-slate-100 overflow-hidden">'''

if old_block in content:
    content = content.replace(old_block, new_block)
    changes.append("client-list view + detail wrapper added")
else:
    print("MISSING: search box + grid start block")

# Filter unifiedRepos by selectedClientKey INSIDE the grouping IIFE, right where searchQuery filter happens
old_filter = '''                  const q = searchQuery.trim().toLowerCase();
                  const filtered = q
                    ? unifiedRepos.filter(
                        (r) =>
                          groupLabel(r.source).toLowerCase().includes(q) ||
                          r.name.toLowerCase().includes(q)
                      )
                    : unifiedRepos;'''

new_filter = '''                  const q = searchQuery.trim().toLowerCase();
                  const byClient = selectedClientKey
                    ? unifiedRepos.filter((r) => clientKey(r.source) === selectedClientKey)
                    : unifiedRepos;
                  const filtered = q
                    ? byClient.filter(
                        (r) =>
                          groupLabel(r.source).toLowerCase().includes(q) ||
                          r.name.toLowerCase().includes(q)
                      )
                    : byClient;'''

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    changes.append("grouping filter updated to respect selectedClientKey")
else:
    print("MISSING: searchQuery filter inside grouping IIFE")

# Close the extra conditional wrapper we opened around the grid
old_close = '''                        ))}
                    </div>
                    );
                  });
                })()}
            </div>
          </div>

          <div className="md:col-span-2">'''

new_close = '''                        ))}
                    </div>
                    );
                  });
                })()}
            </div>
          </div>

          <div className="md:col-span-2">'''

# find the true end of the two-column grid (closing </div></div> after selected repo panel) to add closing brace
old_grid_end = '''            {selected &&
              !loadingEnv &&
              envFiles.map((file) => ('''

if old_grid_end not in content:
    print("MISSING: grid end marker for closing brace insertion")
else:
    changes.append("grid end marker found (closing brace handled separately)")

if len(changes) >= 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PARTIAL/SUCCESS:", changes)
else:
    print("ABORTED - not enough changes matched. Applied so far:", changes)
