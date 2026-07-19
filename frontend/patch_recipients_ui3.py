path = "/var/www/fullstack/pm2-dashboard_dev/frontend/components/Navbar.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

marker = "function NotificationBell() {"

new_code = '''interface RecipientItem {
  id: number;
  email: string;
}

function RecipientsModal({ onClose }: { onClose: () => void }) {
  const [recipients, setRecipients] = useState<RecipientItem[]>([]);
  const [newEmail, setNewEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<RecipientItem[]>("/notifications/recipients");
      setRecipients(res.data);
    } catch {
      setError("Could not load recipients.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function addRecipient(e: React.FormEvent) {
    e.preventDefault();
    if (!newEmail.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.post("/notifications/recipients", { email: newEmail.trim() });
      setNewEmail("");
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not add that email.");
    } finally {
      setSaving(false);
    }
  }

  async function removeRecipient(id: number) {
    try {
      await api.delete(`/notifications/recipients/${id}`);
      setRecipients((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError("Could not remove that recipient.");
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 z-30 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-md p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">Email notification recipients</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-lg leading-none">
            &times;
          </button>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Everyone in this list gets an email as soon as a new PM2 crash or SSL certificate
          expiring soon (within 24h) is detected.
        </p>

        <form onSubmit={addRecipient} className="flex gap-2 mb-4">
          <input
            type="email"
            required
            placeholder="someone@example.com"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="flex-1 border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm"
          />
          <button type="submit" disabled={saving} className="btn-primary text-sm px-3">
            {saving ? "Adding…" : "Add"}
          </button>
        </form>

        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}
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
}

function NotificationBell() {'''

if marker in content and "RecipientsModal" not in content:
    content = content.replace(marker, new_code)
    changes.append("RecipientsModal added")
else:
    print("MISSING or already present: NotificationBell marker")

old_state = "  const [open, setOpen] = useState(false);"
new_state = old_state + "\n  const [showRecipients, setShowRecipients] = useState(false);"
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("showRecipients state added")
else:
    print("MISSING: NotificationBell open state line")

old_header = '''          <div className="px-4 py-3 border-b border-slate-100">
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Notifications</p>
            <p className="text-xs text-slate-400">
              {total === 0 ? "All clear" : `${total} item${total === 1 ? "" : "s"} need attention`}
            </p>
          </div>'''

new_header = '''          <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Notifications</p>
              <p className="text-xs text-slate-400">
                {total === 0 ? "All clear" : `${total} item${total === 1 ? "" : "s"} need attention`}
              </p>
            </div>
            <button
              onClick={() => {
                setShowRecipients(true);
                setOpen(false);
              }}
              className="text-xs text-brand-600 dark:text-brand-400 hover:text-brand-800 shrink-0"
            >
              Manage recipients
            </button>
          </div>'''

if old_header in content:
    content = content.replace(old_header, new_header)
    changes.append("Manage recipients link added")
else:
    print("MISSING: dropdown header block")

old_close = '''      )}
    </div>
  );
}

export default function Navbar'''

new_close = '''      )}
      {showRecipients && <RecipientsModal onClose={() => setShowRecipients(false)} />}
    </div>
  );
}

export default function Navbar'''

if old_close in content:
    content = content.replace(old_close, new_close)
    changes.append("modal render wired in")
else:
    print("MISSING: NotificationBell closing block")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
