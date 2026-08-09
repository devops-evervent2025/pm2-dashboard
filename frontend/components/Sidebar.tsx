"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useState } from "react";
import QuickDeployModal from "@/components/QuickDeployModal";

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
          ? "bg-brand-50 text-brand-700 dark:bg-slate-800 dark:text-brand-400"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      }`}
    >
      <span className="w-5 h-5 flex items-center justify-center shrink-0">{icon}</span>
      {label}
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const { role } = useAuth();
  const [showQuickDeploy, setShowQuickDeploy] = useState(false);

  const isDashboardActive =
    pathname === "/dashboard" ||
    (pathname.startsWith("/dashboard/") &&
      !pathname.startsWith("/dashboard/alerts") &&
      !pathname.startsWith("/dashboard/users") &&
      !pathname.startsWith("/dashboard/repos") &&
      !pathname.startsWith("/dashboard/ssl") &&
      !pathname.startsWith("/dashboard/app-logs") &&
      !pathname.startsWith("/dashboard/resources") &&
      !pathname.startsWith("/dashboard/docker") &&
      !pathname.startsWith("/dashboard/k8s"));
  const isDockerDashboardActive = pathname.startsWith("/dashboard/docker");
  const isK8sDashboardActive = pathname.startsWith("/dashboard/k8s");
  const isAlertsActive = pathname.startsWith("/dashboard/alerts");
  const isReposActive = pathname.startsWith("/dashboard/repos");
  const isSslActive = pathname.startsWith("/dashboard/ssl");
  const isTerminalActive = pathname.startsWith("/dashboard/terminal");
  const isAppLogsActive = pathname.startsWith("/dashboard/app-logs");
  const isResourcesActive = pathname.startsWith("/dashboard/resources");

  return (
    <aside className="w-56 shrink-0 bg-white border-r border-slate-200 min-h-screen py-6 px-3 hidden sm:block dark:bg-slate-900 dark:border-slate-700">
      <div className="px-3 mb-6">
        <span className="font-semibold text-slate-800 dark:text-slate-100">PM2 Dashboard</span>
      </div>
      <nav className="space-y-1">
        <NavItem
          href="/dashboard"
          label="PM2 Dashboard"
          active={isDashboardActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M3 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM11 4a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V4zM3 12a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H4a1 1 0 01-1-1v-4zM11 12a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/docker"
          label="Docker Dashboard"
          active={isDockerDashboardActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M4 8h2v2H4V8zm3 0h2v2H7V8zm3 0h2v2h-2V8zm3 0h2v2h-2V8zM4 5h2v2H4V5zm3 0h2v2H7V5zm3 0h2v2h-2V5zM2 10.5S2.5 15 10 15s8-4.5 8-4.5-1 1.5-8 1.5-8-1.5-8-1.5z" />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/k8s"
          label="Kubernetes Dashboard"
          active={isK8sDashboardActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path d="M10 1.5l7.5 4.3v8.4L10 18.5l-7.5-4.3V5.8L10 1.5zM10 3.6L4 7v6l6 3.4 6-3.4V7l-6-3.4zM10 6a4 4 0 100 8 4 4 0 000-8z" />
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
          href="/dashboard/terminal"
          label="Server Terminal"
          active={isTerminalActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M2 4a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V4zm3.28 2.22a.75.75 0 00-1.06 1.06L6.44 9.5l-2.22 2.22a.75.75 0 101.06 1.06l2.75-2.75a.75.75 0 000-1.06L5.28 6.22zM9.5 12.25a.75.75 0 000 1.5h4a.75.75 0 000-1.5h-4z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
        <NavItem
          href="/dashboard/app-logs"
          label="App Logs"
          active={isAppLogsActive}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path
                fillRule="evenodd"
                d="M4 4a2 2 0 012-2h5.586A2 2 0 0113 2.586L15.414 5A2 2 0 0116 6.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 5a1 1 0 000 2h6a1 1 0 100-2H7zm0 4a1 1 0 100 2h6a1 1 0 100-2H7z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
        {role === "admin" && (
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
        )}
        {role === "admin" && (
          <NavItem
            href="/dashboard/activity"
            label="Activity Log"
            active={pathname.startsWith("/dashboard/activity")}
            icon={
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                  clipRule="evenodd"
                />
              </svg>
            }
          />
        )}
        {role === "admin" && (
          <NavItem
            href="/dashboard/resources"
            label="Resources"
            active={isResourcesActive}
            icon={
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path d="M3 12h2v6H3v-6zm4-4h2v10H7V8zm4-4h2v14h-2V4zm4 7h2v7h-2v-7z" />
              </svg>
            }
          />
        )}
        {(role === "admin" || role === "developer") && (
          <button
            type="button"
            onClick={() => setShowQuickDeploy(true)}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors text-slate-600 hover:bg-slate-100 hover:text-slate-800 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
          >
            <span className="w-5 h-5 flex items-center justify-center shrink-0">
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path d="M10 2a1 1 0 01.894.553l7 14A1 1 0 0117 18H3a1 1 0 01-.894-1.447l7-14A1 1 0 0110 2z" />
              </svg>
            </span>
            Quick Deploy
          </button>
        )}
      </nav>
      {showQuickDeploy && <QuickDeployModal onClose={() => setShowQuickDeploy(false)} />}
    </aside>
  );
}
