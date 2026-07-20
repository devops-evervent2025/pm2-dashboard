path = "/var/www/fullstack/pm2-dashboard_dev/frontend/components/Navbar.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add showList + confirmingId state
old_state = '''  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);'''
new_state = '''  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showList, setShowList] = useState(false);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);'''
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("state added")
else:
    print("MISSING: RecipientsModal state block")

# 2. Update removeRecipient to require confirmation first
old_remove = '''  async function removeRecipient(id: number) {
    try {
      await api.delete(`/notifications/recipients/${id}`);
      setRecipients((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError("Could not remove that recipient.");
    }
  }'''
new_remove = '''  async function confirmRemove(id: number) {
    try {
      await api.delete(`/notifications/recipients/${id}`);
      setRecipients((prev) => prev.filter((r) => r.id !== id));
      setConfirmingId(null);
    } catch {
      setError("Could not remove that recipient.");
    }
  }'''
if old_remove in content:
    content = content.replace(old_remove, new_remove)
    changes.append("removeRecipient renamed to confirmRemove")
else:
    print("MISSING: removeRecipient function")

# 3. Replace the always-visible list with a "View recipients" button + conditional popup
old_list_section = '''        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}
        {loading && <p className="text-xs text-slate-400">Loading…</p>}

        {!loading && recipients.length === 0 && (
          <p className="text-xs text-slate-400">No recipients yet - add one above.</p>
        )}

        <div className="space-y-1.5 max-h-60 overflow-y-auto">
          {recipients.map((r) => (
            <div key={r.id} className="flex items-center justify-between px-2 py-1.5 rounded-md bg-slate-50 dark:bg-slate-800">
              <span className="text-sm text-slate-700 dark:text-slate-200">{r.email}</span>
              <button
                onClick={() => removeRecipient(r.id)}
                className="text-xs text-red-500 hover:text-red-700"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}'''

new_list_section = '''        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

        {!loading && (
          <button
            onClick={() => setShowList(true)}
            className="btn-secondary text-sm w-full"
          >
            View recipients ({recipients.length})
          </button>
        )}
        {loading && <p className="text-xs text-slate-400">Loading…</p>}
      </div>

      {showList && (
        <div
          className="fixed inset-0 bg-black/30 z-40 flex items-center justify-center p-4"
          onClick={() => setShowList(false)}
        >
          <div
            className="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-sm p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                Recipients ({recipients.length})
              </h3>
              <button
                onClick={() => {
                  setShowList(false);
                  setConfirmingId(null);
                }}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            {recipients.length === 0 && (
              <p className="text-xs text-slate-400">No recipients yet.</p>
            )}

            <div className="space-y-1.5 max-h-72 overflow-y-auto">
              {recipients.map((r) => (
                <div key={r.id} className="px-2 py-1.5 rounded-md bg-slate-50 dark:bg-slate-800">
                  {confirmingId === r.id ? (
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-slate-600 dark:text-slate-300">
                        Remove {r.email}?
                      </span>
                      <div className="flex gap-2 shrink-0">
                        <button
                          onClick={() => confirmRemove(r.id)}
                          className="text-xs text-white bg-red-600 hover:bg-red-700 px-2 py-1 rounded-md"
                        >
                          Yes, remove
                        </button>
                        <button
                          onClick={() => setConfirmingId(null)}
                          className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-700 dark:text-slate-200">{r.email}</span>
                      <button
                        onClick={() => setConfirmingId(r.id)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}'''

if old_list_section in content:
    content = content.replace(old_list_section, new_list_section)
    changes.append("list hidden behind button + confirmation popup added")
else:
    print("MISSING: recipients list section")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
