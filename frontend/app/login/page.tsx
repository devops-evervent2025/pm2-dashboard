"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";
import InfraLinkLogo from "@/components/branding/InfraLinkLogo";

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

export default function LoginPage() {
  const { login, verifyOtp } = useAuth();

  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [maskedEmail, setMaskedEmail] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lockedSeconds, setLockedSeconds] = useState<number | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  // Only animate step transitions AFTER the first paint. Both step
  // panels below always carry "transition-all duration-300" - on the
  // very first render there's nothing to transition FROM, but if a
  // screenshot/paint happens to land inside that first transition
  // window anyway, the panel can render mid-slide (translate-x not yet
  // settled), visually clipping the left edge of its text. Gating the
  // transition classes behind this flag means the initial paint always
  // renders already-settled (opacity-100 translate-x-0), and only
  // switches to animated afterwards, once the user actually changes steps.
  const [animateSteps, setAnimateSteps] = useState(false);
  useEffect(() => {
    if (!mounted) return;
    const t = setTimeout(() => setAnimateSteps(true), 50);
    return () => clearTimeout(t);
  }, [mounted]);

  useEffect(() => {
    if (lockedSeconds === null) return;
    if (lockedSeconds <= 0) {
      setLockedSeconds(null);
      setError(null);
      return;
    }
    intervalRef.current = setInterval(() => {
      setLockedSeconds((prev) => (prev !== null ? prev - 1 : null));
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lockedSeconds]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(t);
  }, [resendCooldown]);

  async function handleCredentialsSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { maskedEmail: masked, otpRequired } = await login(username, password);
      if (!otpRequired) return;
      setMaskedEmail(masked);
      setStep("otp");
      setResendCooldown(60);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail && typeof detail === "object" && "retry_after_seconds" in detail) {
        setLockedSeconds(detail.retry_after_seconds);
        setError(detail.message || "Account locked due to too many failed attempts.");
      } else {
        setError(typeof detail === "string" ? detail : "Login failed");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await verifyOtp(username, code);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setError(null);
    setLoading(true);
    try {
      const { maskedEmail: masked } = await login(username, password);
      setMaskedEmail(masked);
      setCode("");
      setResendCooldown(60);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not resend the code");
    } finally {
      setLoading(false);
    }
  }

  function backToCredentials() {
    setStep("credentials");
    setCode("");
    setError(null);
  }

  // Client-side navigation (e.g. after logout) can carry over a
  // horizontal/vertical scroll position from the previous page. The
  // browser's own automatic scroll restoration can also re-apply an old
  // position AFTER this component mounts, so we both disable that and
  // force every scroll container back to (0, 0) directly.
  useEffect(() => {
    if (typeof window !== "undefined" && "scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual";
    }
    window.scrollTo(0, 0);
    document.documentElement.scrollLeft = 0;
    document.documentElement.scrollTop = 0;
    document.body.scrollLeft = 0;
    document.body.scrollTop = 0;
  }, []);

  const isLocked = lockedSeconds !== null && lockedSeconds > 0;

  // Renders nothing until the client has fully mounted and Tailwind's
  // CSS has applied. Without this, there's a brief window where the
  // HTML paints before position:relative lands on this wrapper - the
  // background blobs below (position:absolute, -left-40) then measure
  // against <body> instead, which can widen the scrollable area
  // leftward for a moment and leave the viewport offset, cropping the
  // card's left edge until a refresh re-primes the CSS cache.
  if (!mounted) {
    return <div className="min-h-screen bg-slate-950" />;
  }

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 bg-slate-950">
      <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-950 via-slate-950 to-purple-950" />
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/30 rounded-full blur-3xl animate-blob" />
        <div className="absolute -bottom-40 -right-32 w-96 h-96 bg-purple-600/30 rounded-full blur-3xl animate-blob animation-delay-2000" />
        <div className="absolute top-1/3 right-1/4 w-72 h-72 bg-brand-500/20 rounded-full blur-3xl animate-blob animation-delay-4000" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
      </div>

      <div className="relative w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="relative inline-flex items-center justify-center mb-2 animate-scale-in">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-brand-500/40 to-indigo-600/40 blur-2xl animate-pulse" />
            <InfraLinkLogo
              variant="full"
              className="relative h-28 w-auto object-contain drop-shadow-[0_0_25px_rgba(99,102,241,0.5)]"
            />
          </div>
        </div>

        <div className="rounded-2xl bg-white/[0.07] backdrop-blur-xl border border-white/10 shadow-2xl p-8">
          <div className="relative">
            <div
              className={`${animateSteps ? "transition-all duration-300 ease-out" : ""} ${
                step === "credentials" ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4 absolute inset-0 pointer-events-none"
              }`}
            >
              <p className="text-sm text-slate-300 mb-6">Sign in to manage your clients & servers</p>
              <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Username</label>
                  <input
                    className="w-full rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-brand-400 focus:bg-white/10"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    disabled={isLocked}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
                  <input
                    type="password"
                    className="w-full rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-brand-400 focus:bg-white/10"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLocked}
                  />
                </div>

                {error && (
                  <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 animate-shake">
                    <p>{error}</p>
                    {isLocked && (
                      <p className="mt-1 font-medium">
                        Try again in {formatCountdown(lockedSeconds as number)}
                      </p>
                    )}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || isLocked}
                  className="w-full relative rounded-lg bg-gradient-to-r from-brand-500 to-indigo-600 text-white text-sm font-medium py-2.5 shadow-lg shadow-brand-500/25 transition-all hover:shadow-brand-500/40 hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
                >
                  {isLocked
                    ? `Locked - ${formatCountdown(lockedSeconds as number)}`
                    : loading
                    ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Signing in…
                      </span>
                    )
                    : "Sign in"}
                </button>
              </form>
            </div>

            <div
              className={`${animateSteps ? "transition-all duration-300 ease-out" : ""} ${
                step === "otp" ? "opacity-100 translate-x-0" : "opacity-0 translate-x-4 absolute inset-0 pointer-events-none"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-brand-400">
                  <rect x="3" y="5" width="18" height="14" rx="2" />
                  <path d="m3 7 9 6 9-6" />
                </svg>
                <p className="text-sm text-slate-300">Enter the 6-digit code we sent to</p>
              </div>
              <p className="text-sm font-medium text-white mb-6">{maskedEmail || "your email"}</p>
              <form onSubmit={handleOtpSubmit} className="space-y-4">
                <div>
                  <input
                    className="w-full rounded-lg bg-white/5 border border-white/10 text-white text-center text-2xl tracking-[0.5em] font-mono py-3 outline-none transition-colors focus:border-brand-400 focus:bg-white/10"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="------"
                    required
                    autoFocus
                  />
                </div>

                {error && (
                  <p className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 animate-shake">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading || code.length !== 6}
                  className="w-full rounded-lg bg-gradient-to-r from-brand-500 to-indigo-600 text-white text-sm font-medium py-2.5 shadow-lg shadow-brand-500/25 transition-all hover:shadow-brand-500/40 hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
                >
                  {loading ? "Verifying…" : "Verify & sign in"}
                </button>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                  <button type="button" onClick={backToCredentials} className="hover:text-slate-200 transition-colors">
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={loading || resendCooldown > 0}
                    className="hover:text-slate-200 transition-colors disabled:text-slate-600 disabled:hover:text-slate-600"
                  >
                    {resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : "Resend code"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
