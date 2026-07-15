"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

const ROLE_STYLES: Record<string, string> = {
  admin: "bg-purple-100 text-purple-700",
  developer: "bg-blue-100 text-blue-700",
  viewer: "bg-slate-100 text-slate-600",
};

export default function Navbar({ crumbs }: { crumbs?: { label: string; href?: string }[] }) {
  const { username, role, logout } = useAuth();

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm">
          <Link href="/dashboard" className="font-semibold text-slate-800">
            PM2 Dashboard
          </Link>
          {crumbs?.map((c, i) => (
            <span key={i} className="flex items-center gap-3 text-slate-400">
              <span>/</span>
              {c.href ? (
                <Link href={c.href} className="text-slate-500 hover:text-slate-800">
                  {c.label}
                </Link>
              ) : (
                <span className="text-slate-700 font-medium">{c.label}</span>
              )}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {role === "admin" && (
            <Link href="/dashboard/users" className="text-sm text-slate-500 hover:text-slate-800">
              Manage Users
            </Link>
          )}
          {role && <span className={`badge ${ROLE_STYLES[role]}`}>{role}</span>}
          <span className="text-sm text-slate-600">{username}</span>
          <button onClick={logout} className="btn-secondary text-xs">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
