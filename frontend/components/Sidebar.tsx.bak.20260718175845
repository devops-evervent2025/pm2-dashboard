"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function NavItem({
  href,
  label,
  icon,
  active,
}: {
  href: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
        active
          ? "bg-brand-50 text-brand-700"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-800"
      }`}
    >
      <span className="w-5 h-5 flex items-center justify-center shrink-0">{icon}</span>
      {label}
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();

  const isDashboardActive =
    pathname === "/dashboard" ||
    (pathname.startsWith("/dashboard/") &&
      !pathname.startsWith("/dashboard/alerts") &&
      !pathname.startsWith("/dashboard/users") &&
      !pathname.startsWith("/dashboard/repos") &&
      !pathname.startsWith("/dashboard/ssl"));
  const isAlertsActive = pathname.startsWith("/dashboard/alerts");
  const isReposActive = pathname.startsWith("/dashboard/repos");
  const isSslActive = pathname.startsWith("/dashboard/ssl");

  return (
    <aside className="w-56 shrink-0 bg-white border-r border-slate-200 min-h-screen py-6 px-3 hidden sm:block">
      <div className="px-3 mb-6">
        <span className="font-semibold text-slate-800">PM2 Dashboard</span>
      </div>
      <nav className="space-y-1">
        <NavItem
          href="/dashboard"
          label="Dashboard"
          active={isDashboardActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M3 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM11 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V4zM3 12a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1v-4zM11 12a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/alerts"
          label="Alerts"
          active={isAlertsActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l6.518 11.598c.75 1.334-.213 2.98-1.742 2.98H3.48c-1.53 0-2.492-1.646-1.743-2.98L8.257 3.1zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/repos"
          label="Repos & Env"
          active={isReposActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/ssl"
          label="SSL Dashboard"
          active={isSslActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
      </nav>
    </aside>
  );
}
