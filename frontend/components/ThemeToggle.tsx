"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  // पहले null रखते हैं ताकि सर्वर/client के बीच mismatch (hydration warning) न आए -
  // असली value सिर्फ client पर mount होने के बाद पता चलती है (localStorage से)
  const [isDark, setIsDark] = useState<boolean | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = stored === "dark" || (!stored && prefersDark);
    setIsDark(dark);
    document.documentElement.classList.toggle("dark", dark);
  }, []);

  function toggle() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  if (isDark === null) {
    // पहले render पर कुछ नहीं दिखाते (mount होने तक), ताकि गलत icon flash न हो
    return <span className="w-9 h-9 inline-block" />;
  }

  return (
    <button
      onClick={toggle}
      className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {isDark ? (
        // Sun icon (dark में हैं, light mode पर जाने के लिए)
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
          <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-9.9a1 1 0 010 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 9a1 1 0 110 2h-1a1 1 0 110-2h1zM4.464 4.05l-.707.707a1 1 0 011.414 1.414l.707-.707A1 1 0 004.464 4.05zM4 9a1 1 0 110 2H3a1 1 0 110-2h1zm.464 6.95a1 1 0 001.414 0l.707-.707a1 1 0 00-1.414-1.414l-.707.707a1 1 0 000 1.414zM10 16a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1z" />
        </svg>
      ) : (
        // Moon icon (light में हैं, dark mode पर जाने के लिए)
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      )}
    </button>
  );
}
