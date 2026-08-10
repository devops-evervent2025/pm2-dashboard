"use client";

/**
 * Centralized InfraLink branding component. This is the ONLY place in
 * the app that should ever know a logo filename or path - every page/
 * component just renders <InfraLinkLogo /> or <InfraLinkLogo variant=".."/>
 * and never imports an <img src="/something.png"> directly. Changing
 * the brand later means replacing files in public/branding/ (or the
 * BRANDING map below if the extension/filenames change) - nothing else
 * in the app needs to change.
 *
 * Theme awareness: there's no global theme context in this app -
 * ThemeToggle.tsx toggles a "dark" class directly on <html> and persists
 * the choice in localStorage. This component mirrors that exact
 * mechanism: it reads the class on mount, then watches it with a
 * MutationObserver so the logo swaps immediately if the theme changes
 * anywhere else in the app, without needing a shared context provider.
 */
import { useEffect, useState } from "react";
import { BRANDING, APP_NAME } from "./config";

export { APP_NAME };

function useIsDarkMode(): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    setIsDark(root.classList.contains("dark"));

    const observer = new MutationObserver(() => {
      setIsDark(root.classList.contains("dark"));
    });
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });

    return () => observer.disconnect();
  }, []);

  return isDark;
}

type Variant = "full" | "icon";

export default function InfraLinkLogo({
  variant = "full",
  className = "",
  alt,
}: {
  variant?: Variant;
  className?: string;
  alt?: string;
}) {
  const isDark = useIsDarkMode();

  const src =
    variant === "icon"
      ? isDark
        ? BRANDING.iconDark
        : BRANDING.iconLight
      : isDark
      ? BRANDING.logoDark
      : BRANDING.logoLight;

  return (
    <img
      src={src}
      alt={alt || APP_NAME}
      className={className || (variant === "icon" ? "h-7 w-auto object-contain" : "h-20 w-auto object-contain")}
    />
  );
}

