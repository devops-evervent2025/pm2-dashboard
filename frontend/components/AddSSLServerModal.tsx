"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function AddSSLServerModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [ipAddress, setIpAddress] = useState("");
  const [sshPort, setSshPort] = useState(22);
  const [sshUsername, setSshUsername] = useState("root");
  const [sshPassword, setSshPassword] = useState("");
  const [sshKeyPath, setSshKeyPath] = useState("");
  const [confDir, setConfDir] = useState("/etc/nginx/conf.d");
  const [thresholdDays, setThresholdDays] = useState(7);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/ssl/servers", {
        name,
        ip_address: ipAddress,
        ssh_port: sshPort,
        ssh_username: sshUsername,
        ssh_password: sshPassword || null,
        ssh_private_key_path: sshKeyPath || null,
        conf_dir: confDir,
        threshold_days: thresholdDays,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to add server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20 px-4 overflow-y-auto py-8">
      <div className="card w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">Add SSL Server</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                className="input-field"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Amaze Dev"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">IP address</label>
              <input
                className="input-field"
                placeholder="e.g. 203.0.113.10"
                value={ipAddress}
                onChange={(e) => setIpAddress(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">SSH port</label>
              <input
                type="number"
                className="input-field"
                value={sshPort}
                onChange={(e) => setSshPort(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">SSH username</label>
              <input
                className="input-field"
                value={sshUsername}
                onChange={(e) => setSshUsername(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">SSH password</label>
              <input
                type="password"
                className="input-field"
                value={sshPassword}
                onChange={(e) => setSshPassword(e.target.value)}
                placeholder="leave blank if using a key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Private key path</label>
              <input
                className="input-field"
                value={sshKeyPath}
                onChange={(e) => setSshKeyPath(e.target.value)}
                placeholder="/path/on/backend/host"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Nginx conf directory</label>
              <input
                className="input-field"
                value={confDir}
                onChange={(e) => setConfDir(e.target.value)}
                placeholder="/etc/nginx/conf.d"
                required
              />
              <p className="text-xs text-slate-400 mt-1">
                All *.conf files in this folder will be scanned - every domain found
                will have its certificate expiry checked automatically.
              </p>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Alert threshold (दिन)</label>
              <input
                type="number"
                min={1}
                className="input-field"
                value={thresholdDays}
                onChange={(e) => setThresholdDays(Number(e.target.value))}
              />
              <p className="text-xs text-slate-400 mt-1">
                How many days before expiry to start showing a warning - e.g. 1 or 7.
              </p>
            </div>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
