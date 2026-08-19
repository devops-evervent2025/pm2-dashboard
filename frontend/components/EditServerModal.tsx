"use client";

import { useState } from "react";
import { ServerItem, api } from "@/lib/api";

export default function EditServerModal({
  server,
  onClose,
  onUpdated,
}: {
  server: ServerItem;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [name, setName] = useState(server.name);
  const [ipAddress, setIpAddress] = useState(server.ip_address);
  const [sshPort, setSshPort] = useState(server.ssh_port);
  const [sshUsername, setSshUsername] = useState(server.ssh_username);
  const [sshPassword, setSshPassword] = useState("");
  const [sshKeyPath, setSshKeyPath] = useState("");
  const [pm2Path, setPm2Path] = useState(server.pm2_path || "");
  const [tag, setTag] = useState(server.tag || "");
  const [environment, setEnvironment] = useState<string>(server.environment || "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [detecting, setDetecting] = useState(false);
  const [detectMessage, setDetectMessage] = useState<string | null>(null);
  const [detectOk, setDetectOk] = useState<boolean | null>(null);

  async function handleDetect() {
    setDetecting(true);
    setDetectMessage(null);
    setDetectOk(null);
    try {
      const res = await api.post("/servers/detect-pm2", {
        ip_address: ipAddress,
        ssh_port: sshPort,
        ssh_username: sshUsername,
        ssh_password: sshPassword || null,
        ssh_private_key_path: sshKeyPath || null,
      });
      if (res.data.found) {
        setPm2Path(res.data.pm2_path);
        setDetectOk(true);
        setDetectMessage(`Found: ${res.data.pm2_path}`);
      } else {
        setDetectOk(false);
        setDetectMessage(res.data.detail || "pm2 not found on this server.");
      }
    } catch (err: any) {
      setDetectOk(false);
      setDetectMessage(err?.response?.data?.detail || "Could not connect to test this server.");
    } finally {
      setDetecting(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        name,
        ip_address: ipAddress,
        ssh_port: sshPort,
        ssh_username: sshUsername,
        pm2_path: pm2Path || null,
        tag: tag || null,
        environment: environment || null,
      };
      if (sshPassword) payload.ssh_password = sshPassword;
      if (sshKeyPath) payload.ssh_private_key_path = sshKeyPath;

      await api.patch(`/servers/${server.id}`, payload);
      onUpdated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to update server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20 px-4 overflow-y-auto py-8">
      <div className="card w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">Edit Server</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Server name</label>
              <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">IP address</label>
              <input
                className="input-field"
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
                placeholder="leave blank to keep current"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Private key path</label>
              <input
                className="input-field"
                value={sshKeyPath}
                onChange={(e) => setSshKeyPath(e.target.value)}
                placeholder="leave blank to keep current"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">
                PM2 binary path <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <div className="flex gap-2">
                <input
                  className="input-field"
                  value={pm2Path}
                  onChange={(e) => setPm2Path(e.target.value)}
                  placeholder="leave blank to use pm2 from PATH"
                />
                <button
                  type="button"
                  onClick={handleDetect}
                  disabled={detecting || !ipAddress}
                  className="btn-secondary text-xs whitespace-nowrap"
                >
                  {detecting ? "Checking…" : "Detect"}
                </button>
              </div>
              {detectMessage && (
                <p className={`text-xs mt-1 ${detectOk ? "text-emerald-600" : "text-red-600"}`}>
                  {detectMessage}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Tag (optional)</label>
              <input className="input-field" value={tag} onChange={(e) => setTag(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Environment</label>
              <select
                className="input-field"
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
              >
                <option value="">Auto-detect</option>
                <option value="Dev">Dev</option>
                <option value="Stg">Stg</option>
                <option value="Prod">Prod</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
