path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/terminal.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_block = '''    lowered = raw.lower()
    for marker in BROWSER_COPY_HEADER_MARKERS:
        if marker in lowered:
            return (
                "This looks like a command copied from a browser's 'Copy as cURL' "
                "(it contains session/browser fingerprint headers). Please write a "
                "plain curl command instead - don't paste browser-copied requests."
            )

'''

if old_block in content:
    content = content.replace(old_block, "")
    old_const = '''BROWSER_COPY_HEADER_MARKERS = (
    "cookie:", "sec-ch-ua", "sec-fetch-", "x-client-data", "sec-ch-ua-platform",
)
'''
    content = content.replace(old_const, "")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: browser-copy check removed.")
else:
    print("ERROR: expected block not found - no changes written.")
