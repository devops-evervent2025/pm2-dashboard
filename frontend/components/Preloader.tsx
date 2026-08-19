"use client";

import InfraLinkLogo from "@/components/branding/InfraLinkLogo";
import { APP_NAME } from "@/components/branding/config";

type Size = "xs" | "sm" | "md" | "lg";

const sizeMap: Record<Size, string> = {
  xs: "w-4 h-4",
  sm: "w-5 h-5",
  md: "w-8 h-8",
  lg: "w-12 h-12",
};

export function Spinner({ size = "md", className = "" }: { size?: Size; className?: string }) {
  return (
    <div className={`relative ${sizeMap[size]} ${className}`} role="status" aria-label="Loading">
      <div className="absolute inset-0 rounded-full border-2 border-brand-100 dark:border-brand-900/40" />
      <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-brand-500 animate-spin" />
      <div className="absolute inset-[3px] rounded-full border-2 border-transparent border-b-brand-400 animate-spin-reverse opacity-70" />
      <span className="sr-only">Loading</span>
    </div>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex gap-1 ml-0.5 align-middle">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1 h-1 rounded-full bg-brand-500 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

/** Advanced full-page animated preloader with InfraLink branding */
export function FullPagePreloader({
  message = "Loading",
  subMessage = "Fetching your infrastructure data",
  overlay = false,
}: {
  message?: string;
  subMessage?: string;
  overlay?: boolean;
}) {
  return (
    <div
      className={`${overlay ? "fixed top-16 left-0 sm:left-56 right-0 bottom-0 z-30" : "fixed inset-0 z-[200]"} flex items-center justify-center overflow-hidden ${
        overlay
          ? "bg-white/80 dark:bg-slate-950/88 backdrop-blur-xl"
          : "bg-gradient-to-br from-slate-50 via-white to-brand-50/40 dark:from-slate-950 dark:via-slate-900 dark:to-brand-950/30"
      }`}
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      {/* Animated background mesh */}
      <div className="absolute inset-0 preloader-mesh opacity-60 dark:opacity-40" />
      <div className="absolute inset-0 preloader-grid opacity-[0.035] dark:opacity-[0.06]" />

      {/* Floating orbs */}
      <div className="absolute top-1/4 -left-16 w-64 h-64 rounded-full bg-brand-400/20 blur-3xl animate-blob" />
      <div className="absolute bottom-1/4 -right-16 w-72 h-72 rounded-full bg-brand-500/15 blur-3xl animate-blob [animation-delay:2s]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-brand-300/10 blur-3xl animate-pulse" />

      {/* Orbiting particles */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <span
            key={i}
            className="absolute w-1.5 h-1.5 rounded-full bg-brand-500/70 preloader-orbit-dot"
            style={{
              animationDelay: `${i * 0.5}s`,
              transform: `rotate(${i * 60}deg) translateX(88px)`,
            }}
          />
        ))}
      </div>

      {/* Main loader card */}
      <div className="relative flex flex-col items-center gap-8 px-6 animate-fade-in-up">
        {/* Orbiting rings + logo */}
        <div className="relative flex items-center justify-center w-36 h-36">
          <div className="absolute inset-0 rounded-full border border-brand-200/50 dark:border-brand-800/40 preloader-ring-outer" />
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-brand-500/80 border-r-brand-400/40 animate-spin-slow" />
          <div className="absolute inset-5 rounded-full border-2 border-transparent border-b-brand-600/70 border-l-brand-300/30 animate-spin-reverse" />
          <div className="absolute inset-8 rounded-full bg-brand-500/5 dark:bg-brand-400/10 animate-pulse" />
          <div className="relative z-10 flex items-center justify-center w-16 h-16 rounded-2xl bg-white/90 dark:bg-slate-900/90 shadow-lg shadow-brand-500/10 border border-brand-100/80 dark:border-brand-800/50 backdrop-blur-sm preloader-logo-float">
            <InfraLinkLogo variant="icon" className="h-9 w-auto object-contain" />
          </div>
        </div>

        {/* Text */}
        <div className="text-center space-y-2 max-w-sm">
          <p className="text-lg font-semibold text-slate-800 dark:text-slate-100 tracking-tight">
            {message}
            <LoadingDots />
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 preloader-text-shimmer">{subMessage}</p>
        </div>

        {/* Animated progress bar */}
        <div className="w-56 h-1 rounded-full bg-slate-200/80 dark:bg-slate-700/80 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600 preloader-progress-bar" />
        </div>

        <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 font-medium">
          {APP_NAME}
        </p>
      </div>
    </div>
  );
}

/** Alias – standalone full-screen loader */
export function PageLoader({ message = "Loading", subMessage }: { message?: string; subMessage?: string }) {
  return <FullPagePreloader message={message} subMessage={subMessage || "Please wait while we prepare your dashboard"} />;
}

/** Overlay for in-page initial data fetch */
export function PageLoadingOverlay({
  show,
  message = "Loading",
  subMessage,
}: {
  show: boolean;
  message?: string;
  subMessage?: string;
}) {
  if (!show) return null;
  return (
    <FullPagePreloader
      message={message}
      subMessage={subMessage || "This may take a few seconds"}
      overlay
    />
  );
}

export function LoadingState({
  message = "Loading",
  variant = "section",
  size = "md",
}: {
  message?: string;
  variant?: "section" | "inline" | "compact";
  size?: Size;
}) {
  if (variant === "inline") {
    return (
      <div className="inline-flex items-center gap-2.5">
        <Spinner size={size === "md" ? "sm" : size} />
        <span className="text-sm text-slate-500 dark:text-slate-400">
          {message}
          <LoadingDots />
        </span>
      </div>
    );
  }

  if (variant === "compact") {
    return (
      <div className="flex items-center justify-center gap-2 py-4">
        <Spinner size="sm" />
        <span className="text-xs text-slate-400">
          {message}
          <LoadingDots />
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 animate-fade-in-up">
      <div className="relative">
        <div className="absolute -inset-4 rounded-full bg-brand-500/10 animate-pulse" />
        <Spinner size="lg" />
      </div>
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
        {message}
        <LoadingDots />
      </p>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card p-5 flex flex-col gap-3 overflow-hidden">
      <div className="flex justify-between items-center">
        <div className="h-5 w-32 rounded-lg skeleton-shimmer" />
        <div className="h-5 w-16 rounded-full skeleton-shimmer" />
      </div>
      <div className="h-4 w-full rounded skeleton-shimmer" />
      <div className="h-4 w-2/3 rounded skeleton-shimmer" />
      <div className="h-3 w-24 rounded mt-2 skeleton-shimmer" />
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-fade-in-up">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonList({ count = 4 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3 animate-fade-in-up">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4 flex items-center gap-4 overflow-hidden">
          <div className="h-10 w-10 rounded-full skeleton-shimmer shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-40 rounded skeleton-shimmer" />
            <div className="h-3 w-64 rounded skeleton-shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}

