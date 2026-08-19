"use client";

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
      <div className="absolute inset-0 rounded-full border-2 border-slate-200 dark:border-slate-600" />
      <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-brand-500 animate-spin" />
      <span className="sr-only">Loading</span>
    </div>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex gap-0.5 ml-0.5">
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

/** Compact pill loader – spinner + label (like refresh/scanning button style) */
export function LoaderPill({ message = "Loading" }: { message?: string }) {
  return (
    <div
      className="inline-flex items-center gap-3 px-5 py-2.5 rounded-2xl bg-slate-100/95 dark:bg-slate-800/95 border border-slate-200/80 dark:border-slate-700/80 shadow-sm"
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      <Spinner size="sm" />
      <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
        {message}
        <LoadingDots />
      </span>
    </div>
  );
}

/** Full content-area overlay with compact centered pill (navbar + sidebar stay visible) */
export function FullPagePreloader({
  message = "Loading",
  overlay = false,
}: {
  message?: string;
  subMessage?: string;
  overlay?: boolean;
}) {
  return (
    <div
      className={`${
        overlay
          ? "fixed top-16 left-0 sm:left-56 right-0 bottom-0 z-30"
          : "fixed inset-0 z-[200]"
      } flex items-center justify-center bg-white/40 dark:bg-slate-950/40 backdrop-blur-[1px]`}
    >
      <LoaderPill message={message} />
    </div>
  );
}

export function PageLoader({ message = "Loading" }: { message?: string; subMessage?: string }) {
  return <FullPagePreloader message={message} />;
}

export function PageLoadingOverlay({
  show,
  message = "Loading",
}: {
  show: boolean;
  message?: string;
  subMessage?: string;
}) {
  if (!show) return null;
  return <FullPagePreloader message={message} overlay />;
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
  if (variant === "inline" || variant === "compact") {
    return <LoaderPill message={message} />;
  }

  return (
    <div className="flex items-center justify-center py-12">
      <LoaderPill message={message} />
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

