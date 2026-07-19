path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/terminal.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''    if ";" in raw or "&&" in raw or "|" in raw or "`" in raw or "$(" in raw:
        return "Command chaining/piping/substitution is not allowed - a single curl call only."

    return ""'''

new = '''    if _contains_unquoted_chaining(raw):
        return "Command chaining/piping/substitution is not allowed - a single curl call only."

    return ""'''

if old not in content:
    print("ERROR: old chaining check not found - no changes written.")
else:
    content = content.replace(old, new)

    helper = '''

def _contains_unquoted_chaining(raw: str) -> bool:
    """
    Detects shell chaining/piping/substitution characters (; && | ` $() )
    ONLY when they appear outside of a quoted string. A semicolon inside a
    quoted header value (e.g. 'accept-language: en-US,en;q=0.9') is normal
    curl usage and must NOT be blocked - only real, unquoted shell
    metacharacters that could chain another command are dangerous.
    """
    in_squote = False
    in_dquote = False
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if in_squote:
            if c == "'":
                in_squote = False
        elif in_dquote:
            if c == "\\\\" and i + 1 < n:
                i += 1  # skip escaped character
            elif c == '"':
                in_dquote = False
        else:
            if c == "'":
                in_squote = True
            elif c == '"':
                in_dquote = True
            elif c in (";", "|", "`"):
                return True
            elif c == "&" and i + 1 < n and raw[i + 1] == "&":
                return True
            elif c == "$" and i + 1 < n and raw[i + 1] == "(":
                return True
        i += 1
    return False
'''
    # Insert the helper right before _validate_curl_command definition
    marker = "def _validate_curl_command(raw: str) -> str:"
    if marker not in content:
        print("ERROR: could not find insertion point for helper - no changes written.")
    else:
        content = content.replace(marker, helper.strip("\n") + "\n\n\n" + marker)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("SUCCESS: quote-aware chaining check installed.")
