path = "components/Sidebar.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old1 = '  const isSslActive = pathname.startsWith("/dashboard/ssl");'
new1 = old1 + '\n  const isTerminalActive = pathname.startsWith("/dashboard/terminal");'
if old1 in content:
    content = content.replace(old1, new1)
    changes.append("isTerminalActive added")
else:
    print("MISSING: isSslActive line")

old2 = '''        <NavItem
          href="/dashboard/repos"
          label="Repos & Env"
          active={isReposActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
          }
        />
        {role === "admin" && (
          <NavItem
            href="/dashboard/ssl"'''

new2 = '''        <NavItem
          href="/dashboard/repos"
          label="Repos & Env"
          active={isReposActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/terminal"
          label="Server Terminal"
          active={isTerminalActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M2 4a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V4zm3.28 2.22a.75.75 0 00-1.06 1.06L6.44 9.5l-2.22 2.22a.75.75 0 101.06 1.06l2.75-2.75a.75.75 0 000-1.06L5.28 6.22zM9.5 12.25a.75.75 0 000 1.5h4a.75.75 0 000-1.5h-4z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
        {role === "admin" && (
          <NavItem
            href="/dashboard/ssl"'''

if old2 in content:
    content = content.replace(old2, new2)
    changes.append("Server Terminal NavItem inserted")
else:
    print("MISSING: Repos & Env + SSL block")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS - all changes applied:", changes)
else:
    print("ABORTED - not all changes matched, file NOT written. Applied so far:", changes)
