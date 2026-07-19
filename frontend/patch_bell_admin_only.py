path = "/var/www/fullstack/pm2-dashboard_dev/frontend/components/Navbar.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''          {role && <NotificationBell />}'''
new = '''          {role === "admin" && <NotificationBell />}'''

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS")
else:
    print("MISSING - exact line not found")
