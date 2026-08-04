"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchAllResources, ClientResourceItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import ClientResourceCard from "@/components/ClientResourceCard";

export default function ResourcesPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [data, setData] = useState<ClientResourceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAllResources();
      setData(result);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load server resources.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
      return;
    }
    if (!isLoading && role && role !== "admin") {
      router.replace("/dashboard");
      return;
    }
    if (role === "admin") load();
  }, [role, isLoading, router, load]);

  useEffect(() => {
    if (role !== "admin") return;
    const interval = setInterval(load, 60000); // refresh every 60s
    return () => clearInterval(interval);
  }, [role, load]);

  if (isLoading || role !== "admin") {
    return null;
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Server Resources</h1>
            <p className="text-sm text-slate-500">CPU, RAM & Disk usage per client, live via SSH</p>
          </div>
          <button onClick={load} className="badge bg-brand-50 text-brand-600">
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search client..."
          className="w-full max-w-xs rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400"
        />

        {error && <p className="text-sm text-red-500">{error}</p>}

        {loading && data.length === 0 && (
          <p className="text-slate-500">Loading server resources…</p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data
            .filter((client) =>
              client.client_name.toLowerCase().includes(search.toLowerCase())
            )
            .map((client) => (
              <ClientResourceCard key={client.client_id} data={client} />
            ))}
        </div>
      </main>
    </div>
  );
}
