"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Spinner, PageLoader, PageLoadingOverlay, LoadingState } from "@/components/Preloader";

interface ServerOption {
  id: number;
  name: string;
  client_id?: number | null;
  client_name?: string | null;
}

interface AddDomainModalProps {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
  // If set, the server dropdown is pre-filtered to this client's servers
  clientId?: number | "unassigned" | null;
}

export default function AddDomainModal({ open, onClose, onAdded, clientId }: AddDomainModalProps) {
  const [servers, setServers] = useState<ServerOption[]>([]);
  const [serverId, setServerId] = useState<string>("");
  const [domain, setDomain] = useState("");
  const [certPath, setCertPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingServers, setLoadingServers] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setDomain("");
    setCertPath("");
    setLoadingServers(true);
    api
      .get<ServerOption[]>("/ssl/servers")
      .then((res) => {
        setServers(res.data);
        const filtered =
          clientId && clientId !== "unassigned"
            ? res.data.filter((s) => s.client_id === clientId)
            : res.data;
        setServerId(filtered.length > 0 ? String(filtered[0].id) : "");
      })
      .catch(() => setError("Failed to load server list"))
      .finally(() => setLoadingServers(false));
  }, [open, clientId]);

  if (!open) return null;

  const visibleServers =
    clientId && clientId !== "unassigned"
      ? servers.filter((s) => s.client_id === clientId)
      : servers;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!serverId) {
      setError("Please select a server");
      return;
    }
    const trimmed = domain.trim();
    if (!trimmed) {
      setError("Please enter a domain");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.post("/ssl/domains", {
        server_id: Number(serverId),
        domain: trimmed,
        cert_path: certPath.trim() || null,
      });
      onAdded();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to add domain");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="card w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Add domain manually</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Server</label>
            {loadingServers ? (
              <LoadingState message="Loading servers" variant="compact" />
            ) : (
              <select
                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
                value={serverId}
                onChange={(e) => setServerId(e.target.value)}
              >
                {visibleServers.length === 0 && <option value="">No servers available</option>}
                {visibleServers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                    {s.client_name ? ` — ${s.client_name}` : ""}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">Domain</label>
            <input
              type="text"
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              placeholder="example.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">
              Cert path <span className="text-slate-400">(optional)</span>
            </label>
            <input
              type="text"
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              placeholder="/etc/letsencrypt/live/example.com/fullchain.pem"
              value={certPath}
              onChange={(e) => setCertPath(e.target.value)}
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="text-sm px-4 py-2 rounded-md border border-slate-300 text-slate-600 hover:bg-slate-50"
              disabled={loading}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary text-sm" disabled={loading}>
              {loading ? "Adding…" : "Add domain"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
