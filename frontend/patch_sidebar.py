path = "components/Sidebar.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old1 = 'import { usePathname } from "next/navigation";'
new1 = 'import { usePathname } from "next/navigation";\nimport { useAuth } from "@/lib/auth";'
if old1 in content:
    content = content.replace(old1, new1)
    changes.append("import added")
else:
    print("MISSING: usePathname import line")

old2 = "  const pathname = usePathname();"
new2 = "  const pathname = usePathname();\n  const { role } = useAuth();"
if old2 in content:
    content = content.replace(old2, new2)
    changes.append("role hook added")
else:
    print("MISSING: pathname const line")

old_nav = '''        <NavItem
          href="/dashboard/ssl"
          label="SSL Dashboard"
          active={isSslActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                clipRule="evenodd"
              />
            </svg>
          }
        />'''

new_nav = '''        {role === "admin" && (
          <NavItem
            href="/dashboard/ssl"
            label="SSL Dashboard"
            active={isSslActive}
            icon={
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path
                  fillRule="evenodd"
                  d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                  clipRule="evenodd"
                />
              </svg>
            }
          />
        )}'''

if old_nav in content:
    content = content.replace(old_nav, new_nav)
    changes.append("SSL NavItem wrapped")
else:
    print("MISSING: SSL NavItem block (exact match failed)")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS - all 3 changes applied:", changes)
else:
    print("ABORTED - not all changes matched, file NOT written. Applied so far:", changes)
