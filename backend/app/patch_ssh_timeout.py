import shutil
from datetime import datetime

path = "ssh_manager.py"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

# 1. Add socket import (only if not already present)
if "\nimport socket\n" not in content:
    content = content.replace("import json\n", "import json\nimport socket\n", 1)

# 2. Wrap the read in try/except - matches BOTH occurrences of run_restricted_command
old = '''        wrapped = f"bash -lc {shlex.quote(command)}"
        stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        exit_status = stdout.channel.recv_exit_status()
        return {"stdout": out, "stderr": err, "exit_status": exit_status}'''

new = '''        wrapped = f"bash -lc {shlex.quote(command)}"
        stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
        try:
            out = stdout.read().decode(errors="ignore")
            err = stderr.read().decode(errors="ignore")
            exit_status = stdout.channel.recv_exit_status()
        except (socket.timeout, paramiko.buffered_pipe.PipeTimeout):
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s (remote host slow or unreachable).",
                "exit_status": -1,
            }
        return {"stdout": out, "stderr": err, "exit_status": exit_status}'''

count = content.count(old)
if count == 0:
    print("ERROR: expected block not found — aborting, nothing changed.")
elif count != 2:
    print(f"WARNING: expected 2 occurrences, found {count}. Aborting to be safe.")
else:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print(f"Patched {count} occurrence(s) successfully.")
