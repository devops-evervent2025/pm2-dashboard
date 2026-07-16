"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";

export default function PM2LogsDashboardPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
    }
  }, [role, isLoading, router]);

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">PM2 Logs Dashboard</h1>
        <p className="text-sm text-slate-500 mb-6">
          All servers, all processes, one place - coming in the next phase.
        </p>
        <div className="card p-10 text-center text-slate-500">
          🚧 Under construction - this will let you browse and filter logs across every
          server/process without opening each one individually.
        </div>
      </main>
    </div>
  );
}
