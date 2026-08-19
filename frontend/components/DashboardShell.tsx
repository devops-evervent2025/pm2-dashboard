"use client";

import Sidebar from "@/components/Sidebar";
import { SidebarProvider } from "@/lib/sidebar-context";

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</div>
      </div>
    </SidebarProvider>
  );
}
