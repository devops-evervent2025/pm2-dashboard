path = "/var/www/fullstack/pm2-dashboard_dev/frontend/lib/auth.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_effect = '''  useEffect(() => {
    const storedUser = localStorage.getItem("pm2dash_username");
    const storedRole = localStorage.getItem("pm2dash_role") as Role | null;
    if (storedUser && storedRole) {
      setUsername(storedUser);
      setRole(storedRole);
    }
    setIsLoading(false);
  }, []);'''

new_effect = '''  // Auto-logout if the app was closed/inactive for this long, even
  // though the JWT itself might still technically be valid for longer.
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour

  function markActive() {
    localStorage.setItem("pm2dash_last_active", String(Date.now()));
  }

  useEffect(() => {
    const storedUser = localStorage.getItem("pm2dash_username");
    const storedRole = localStorage.getItem("pm2dash_role") as Role | null;
    const lastActiveRaw = localStorage.getItem("pm2dash_last_active");

    if (storedUser && storedRole) {
      const lastActive = lastActiveRaw ? Number(lastActiveRaw) : 0;
      const idleFor = Date.now() - lastActive;

      if (lastActiveRaw && idleFor > IDLE_TIMEOUT_MS) {
        // Was closed/inactive too long - require a fresh login, same as
        // a normal logout, but without redirecting (we're likely already
        // on /login or about to render the app shell).
        localStorage.removeItem("pm2dash_token");
        localStorage.removeItem("pm2dash_role");
        localStorage.removeItem("pm2dash_username");
        localStorage.removeItem("pm2dash_last_active");
      } else {
        setUsername(storedUser);
        setRole(storedRole);
        markActive();
      }
    }
    setIsLoading(false);
  }, []);

  // Keep the "last active" timestamp fresh while the app is actually open
  // and visible - minimizing/switching tabs briefly must NOT count as
  // being closed, only genuinely leaving it untouched for the full hour.
  useEffect(() => {
    if (!username) return;
    const interval = setInterval(markActive, 30 * 1000);
    function onVisibility() {
      if (document.visibilityState === "visible") markActive();
    }
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [username]);'''

if old_effect in content:
    content = content.replace(old_effect, new_effect)
    changes.append("idle-timeout logic added")
else:
    print("MISSING: original useEffect block")

old_verify = '''  async function verifyOtp(usernameInput: string, code: string) {
    const res = await api.post("/auth/otp/verify", { username: usernameInput, code });
    const { access_token, role: userRole, username: uname } = res.data;
    localStorage.setItem("pm2dash_token", access_token);
    localStorage.setItem("pm2dash_role", userRole);
    localStorage.setItem("pm2dash_username", uname);
    setUsername(uname);
    setRole(userRole);
    router.push("/dashboard");
  }'''

new_verify = '''  async function verifyOtp(usernameInput: string, code: string) {
    const res = await api.post("/auth/otp/verify", { username: usernameInput, code });
    const { access_token, role: userRole, username: uname } = res.data;
    localStorage.setItem("pm2dash_token", access_token);
    localStorage.setItem("pm2dash_role", userRole);
    localStorage.setItem("pm2dash_username", uname);
    markActive();
    setUsername(uname);
    setRole(userRole);
    router.push("/dashboard");
  }'''

if old_verify in content:
    content = content.replace(old_verify, new_verify)
    changes.append("verifyOtp marks active on login")
else:
    print("MISSING: verifyOtp function")

old_logout = '''  function logout() {
    localStorage.removeItem("pm2dash_token");
    localStorage.removeItem("pm2dash_role");
    localStorage.removeItem("pm2dash_username");
    setUsername(null);
    setRole(null);
    router.push("/login");
  }'''

new_logout = '''  function logout() {
    localStorage.removeItem("pm2dash_token");
    localStorage.removeItem("pm2dash_role");
    localStorage.removeItem("pm2dash_username");
    localStorage.removeItem("pm2dash_last_active");
    setUsername(null);
    setRole(null);
    router.push("/login");
  }'''

if old_logout in content:
    content = content.replace(old_logout, new_logout)
    changes.append("logout clears last_active too")
else:
    print("MISSING: logout function")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
