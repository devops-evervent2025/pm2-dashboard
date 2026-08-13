"use client";

import { useState } from "react";
import { api, K8sClientItem } from "@/lib/api";

export default function EditK8sClientModal({
  client,
  onClose,
  onUpdated,
}: {
  client: K8sClientItem;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [name, setName] = useState(client.name);
  const [description, setDescription] = useState(client.description || "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.patch(`/k8s-clients/${client.id}`, { name, description: description || null });
      onUpdated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to update client");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20 px-4">
      <div className="card w-full max-w-md p-6">
        <h2 className="font-semibold text-lg mb-4">Edit Kubernetes Client</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Client name</label>
            <input className="input-field" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Description <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <textarea
              className="input-field"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
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
