path = "/var/www/fullstack/pm2-dashboard_dev/frontend/app/login/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add resendCooldown state
old_state = '  const [maskedEmail, setMaskedEmail] = useState<string | null>(null);'
new_state = old_state + '\n  const [resendCooldown, setResendCooldown] = useState(0);'
if old_state in content:
    content = content.replace(old_state, new_state)
    changes.append("resendCooldown state added")
else:
    print("MISSING: maskedEmail state line")

# 2. Add a countdown effect, right after the lockedSeconds effect
old_lock_effect_end = '''    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lockedSeconds]);'''

new_lock_effect_end = '''    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lockedSeconds]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(t);
  }, [resendCooldown]);'''

if old_lock_effect_end in content:
    content = content.replace(old_lock_effect_end, new_lock_effect_end)
    changes.append("countdown effect added")
else:
    print("MISSING: lockedSeconds effect end")

# 3. Start the cooldown whenever a code is (re)sent - both initial send and resend
old_credentials_success = '''      const { maskedEmail: masked } = await login(username, password);
      setMaskedEmail(masked);
      setStep("otp");'''
new_credentials_success = '''      const { maskedEmail: masked } = await login(username, password);
      setMaskedEmail(masked);
      setStep("otp");
      setResendCooldown(60);'''
if old_credentials_success in content:
    content = content.replace(old_credentials_success, new_credentials_success)
    changes.append("cooldown started on initial send")
else:
    print("MISSING: credentials-submit success block")

old_resend_success = '''      const { maskedEmail: masked } = await login(username, password);
      setMaskedEmail(masked);
      setCode("");'''
new_resend_success = '''      const { maskedEmail: masked } = await login(username, password);
      setMaskedEmail(masked);
      setCode("");
      setResendCooldown(60);'''
if old_resend_success in content:
    content = content.replace(old_resend_success, new_resend_success)
    changes.append("cooldown started on resend")
else:
    print("MISSING: resend success block")

# 4. Update the "Resend code" button to be disabled + show countdown
old_resend_button = '''                <button type="button" onClick={handleResend} disabled={loading} className="hover:text-slate-700">
                  Resend code
                </button>'''
new_resend_button = '''                <button
                  type="button"
                  onClick={handleResend}
                  disabled={loading || resendCooldown > 0}
                  className="hover:text-slate-700 disabled:text-slate-600 disabled:hover:text-slate-600"
                >
                  {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : "Resend code"}
                </button>'''
if old_resend_button in content:
    content = content.replace(old_resend_button, new_resend_button)
    changes.append("resend button shows countdown")
else:
    print("MISSING: Resend code button")

if len(changes) == 5:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
