"use client";

import { useState } from "react";
import { api, K8sConnectionType } from "@/lib/api";

export default function AddClusterModal({
  clientId,
  onClose,
  onCreated,
}: {
  clientId: number;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [environment, setEnvironment] = useState("");
  const [connectionType, setConnectionType] = useState<K8sConnectionType>("ssh_kubectl");

  // ssh_kubectl fields
  const [sshIp, setSshIp] = useState("");
  const [sshPort, setSshPort] = useState(22);
  const [sshUsername, setSshUsername] = useState("root");
  const [sshPassword, setSshPassword] = useState("");
  const [sshKeyPath, setSshKeyPath] = useState("");
  const [kubectlPath, setKubectlPath] = useState("");

  // kubeconfig field
  const [kubeconfigYaml, setKubeconfigYaml] = useState("");

  // api_token fields
  const [apiServerUrl, setApiServerUrl] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [apiCaCert, setApiCaCert] = useState("");
  const [apiVerifySsl, setApiVerifySsl] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/k8s-clusters", {
        client_id: clientId,
        name,
        environment: environment || null,
        connection_type: connectionType,
        ssh_ip_address: connectionType === "ssh_kubectl" ? sshIp : null,
        ssh_port: connectionType === "ssh_kubectl" ? sshPort : null,
        ssh_username: connectionType === "ssh_kubectl" ? sshUsername : null,
        ssh_password: connectionType === "ssh_kubectl" ? sshPassword || null : null,
        ssh_private_key_path: connectionType === "ssh_kubectl" ? sshKeyPath || null : null,
        kubectl_path: connectionType === "ssh_kubectl" ? kubectlPath || null : null,
        kubeconfig_yaml: connectionType === "kubeconfig" ? kubeconfigYaml : null,
        api_server_url: connectionType === "api_token" ? apiServerUrl : null,
        api_token: connectionType === "api_token" ? apiToken : null,
        api_ca_cert: connectionType === "api_token" ? apiCaCert || null : null,
        api_verify_ssl: connectionType === "api_token" ? (apiVerifySsl ? "yes" : "no") : null,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create cluster");
    } finally {
      setLoading(false);
    }
  }

  const TAB_STYLES = (active: boolean) =>
    `flex-1 text-sm font-medium py-2 rounded-md transition-colors ${
      active ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
    }`;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20 px-4 overflow-y-auto py-8">
      <div className="card w-full max-w-lg p-6">
        <h2 className="font-semibold text-lg mb-4">Add New Kubernetes Cluster</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Cluster name</label>
            <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Environment (optional)</label>
            <select className="input-field" value={environment} onChange={(e) => setEnvironment(e.target.value)}>
              <option value="">Not set</option>
              <option value="Dev">Dev</option>
              <option value="Stg">Stg</option>
              <option value="Prod">Prod</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">How does this cluster get reached?</label>
            <div className="flex gap-2">
              <button
                type="button"
                className={TAB_STYLES(connectionType === "ssh_kubectl")}
                onClick={() => setConnectionType("ssh_kubectl")}
              >
                SSH + kubectl
              </button>
              <button
                type="button"
                className={TAB_STYLES(connectionType === "kubeconfig")}
                onClick={() => setConnectionType("kubeconfig")}
              >
                Kubeconfig
              </button>
              <button
                type="button"
                className={TAB_STYLES(connectionType === "api_token")}
                onClick={() => setConnectionType("api_token")}
              >
                API + Token
              </button>
            </div>
          </div>

          {connectionType === "ssh_kubectl" && (
            <div className="space-y-3 border-t border-slate-100 pt-3">
              <p className="text-xs text-slate-400">
                SSH into a node that already has kubectl configured and a working kubeconfig,
                and run kubectl commands remotely — same as the PM2/Docker servers.
              </p>
              <div>
                <label className="block text-sm font-medium mb-1">Node IP address</label>
                <input className="input-field" value={sshIp} onChange={(e) => setSshIp(e.target.value)} required />
              </div>
              <div className="grid grid-cols-2 gap-3">
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
                  <input className="input-field" value={sshUsername} onChange={(e) => setSshUsername(e.target.value)} />
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
                  <input className="input-field" value={sshKeyPath} onChange={(e) => setSshKeyPath(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  kubectl binary path <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                  className="input-field"
                  value={kubectlPath}
                  onChange={(e) => setKubectlPath(e.target.value)}
                  placeholder="leave blank to use 'kubectl' from PATH"
                />
              </div>
            </div>
          )}

          {connectionType === "kubeconfig" && (
            <div className="space-y-3 border-t border-slate-100 pt-3">
              <p className="text-xs text-slate-400">
                Paste the full kubeconfig YAML for this cluster. The backend talks to the API
                server directly using this — no SSH involved.
              </p>
              <div>
                <label className="block text-sm font-medium mb-1">Kubeconfig YAML</label>
                <textarea
                  className="input-field font-mono text-xs"
                  rows={10}
                  value={kubeconfigYaml}
                  onChange={(e) => setKubeconfigYaml(e.target.value)}
                  placeholder="apiVersion: v1&#10;clusters:&#10;- cluster: ..."
                  required
                />
              </div>
            </div>
          )}

          {connectionType === "api_token" && (
            <div className="space-y-3 border-t border-slate-100 pt-3">
              <p className="text-xs text-slate-400">
                For cloud-managed clusters where you'd rather not hand out a full kubeconfig —
                just the API server URL and a bearer token.
              </p>
              <div>
                <label className="block text-sm font-medium mb-1">API server URL</label>
                <input
                  className="input-field"
                  placeholder="https://api.mycluster.example.com:6443"
                  value={apiServerUrl}
                  onChange={(e) => setApiServerUrl(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Bearer token</label>
                <textarea
                  className="input-field font-mono text-xs"
                  rows={3}
                  value={apiToken}
                  onChange={(e) => setApiToken(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  CA certificate <span className="text-slate-400 font-normal">(optional, for self-signed clusters)</span>
                </label>
                <textarea
                  className="input-field font-mono text-xs"
                  rows={4}
                  value={apiCaCert}
                  onChange={(e) => setApiCaCert(e.target.value)}
                  placeholder="-----BEGIN CERTIFICATE-----"
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={apiVerifySsl}
                  onChange={(e) => setApiVerifySsl(e.target.checked)}
                />
                Verify SSL certificate
              </label>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Creating…" : "Create cluster"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
