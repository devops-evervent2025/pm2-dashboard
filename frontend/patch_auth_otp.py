path = "/var/www/fullstack/pm2-dashboard_dev/frontend/lib/auth.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_interface = '''interface AuthState {
  username: string | null;
  role: Role | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}'''

new_interface = '''interface AuthState {
  username: string | null;
  role: Role | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ username: string; maskedEmail: string | null }>;
  verifyOtp: (username: string, code: string) => Promise<void>;
  logout: () => void;
}'''

if old_interface in content:
    content = content.replace(old_interface, new_interface)
    changes.append("AuthState interface updated")
else:
    print("MISSING: AuthState interface")

old_login_fn = '''  async function login(usernameInput: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", usernameInput);
    form.append("password", password);
    const res = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { access_token, role: userRole, username: uname } = res.data;
    localStorage.setItem("pm2dash_token", access_token);
    localStorage.setItem("pm2dash_role", userRole);
    localStorage.setItem("pm2dash_username", uname);
    setUsername(uname);
    setRole(userRole);
    router.push("/dashboard");
  }'''

new_login_fn = '''  // Step 1: verifies username+password and triggers the emailed OTP.
  // Does NOT set auth state yet - that only happens after verifyOtp succeeds.
  async function login(usernameInput: string, password: string) {
    const form = new URLSearchParams();
    form.append("username", usernameInput);
    form.append("password", password);
    const res = await api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const { username: uname, masked_email } = res.data;
    return { username: uname, maskedEmail: masked_email ?? null };
  }

  // Step 2: confirms the emailed code and completes sign-in.
  async function verifyOtp(usernameInput: string, code: string) {
    const res = await api.post("/auth/otp/verify", { username: usernameInput, code });
    const { access_token, role: userRole, username: uname } = res.data;
    localStorage.setItem("pm2dash_token", access_token);
    localStorage.setItem("pm2dash_role", userRole);
    localStorage.setItem("pm2dash_username", uname);
    setUsername(uname);
    setRole(userRole);
    router.push("/dashboard");
  }'''

if old_login_fn in content:
    content = content.replace(old_login_fn, new_login_fn)
    changes.append("login/verifyOtp functions updated")
else:
    print("MISSING: old login function")

old_provider_value = '''    <AuthContext.Provider value={{ username, role, isLoading, login, logout }}>'''
new_provider_value = '''    <AuthContext.Provider value={{ username, role, isLoading, login, verifyOtp, logout }}>'''
if old_provider_value in content:
    content = content.replace(old_provider_value, new_provider_value)
    changes.append("provider value updated")
else:
    print("MISSING: AuthContext.Provider value line")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
