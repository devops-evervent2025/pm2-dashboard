path = "/var/www/fullstack/pm2-dashboard_dev/frontend/lib/auth.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_interface = '''  login: (username: string, password: string) => Promise<{ username: string; maskedEmail: string | null }>;'''
new_interface = '''  login: (username: string, password: string) => Promise<{ username: string; maskedEmail: string | null; otpRequired: boolean }>;'''
if old_interface in content:
    content = content.replace(old_interface, new_interface)
    changes.append("interface updated")
else:
    print("MISSING: login interface line")

old_login_fn = '''  async function login(usernameInput: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", usernameInput);
    form.append("password", password);
    const res = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { username: uname, masked_email } = res.data;
    return { username: uname, maskedEmail: masked_email ?? null };
  }'''

new_login_fn = '''  async function login(usernameInput: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", usernameInput);
    form.append("password", password);
    const res = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { username: uname, masked_email, otp_required, access_token, role: userRole } = res.data;

    if (otp_required === false && access_token) {
      // Within the 1-hour grace period - the backend already issued a
      // real token, no OTP screen needed.
      localStorage.setItem("pm2dash_token", access_token);
      localStorage.setItem("pm2dash_role", userRole);
      localStorage.setItem("pm2dash_username", uname);
      markActive();
      setUsername(uname);
      setRole(userRole);
      router.push("/dashboard");
      return { username: uname, maskedEmail: null, otpRequired: false };
    }

    return { username: uname, maskedEmail: masked_email ?? null, otpRequired: true };
  }'''

if old_login_fn in content:
    content = content.replace(old_login_fn, new_login_fn)
    changes.append("login function updated for grace period")
else:
    print("MISSING: old login function")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
