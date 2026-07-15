"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function AddUserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "developer" | "viewer">("viewer");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/auth/users", {
        username,
        email: email || null,
        password,
        role,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create user");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20 px-4">
      <div className="card w-full max-w-md p-6">
        <h2 className="font-semibold text-lg mb-4">Add New User</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              className="input-field"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Email <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input
              type="email"
              className="input-field"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              className="input-field"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Role</label>
            <select
              className="input-field"
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "developer" | "viewer")}
            >
              <option value="viewer">Viewer — read-only, can view processes & logs</option>
              <option value="developer">Developer — can also restart/stop/start processes</option>
              <option value="admin">Admin — full access, can add clients/servers/users</option>
            </select>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Creating…" : "Create user"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
