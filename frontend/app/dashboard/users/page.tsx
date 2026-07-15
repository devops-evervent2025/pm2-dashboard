"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, UserItem, Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import AddUserModal from "@/components/AddUserModal";

const ROLE_STYLES: Record<string, string> = {
  admin: "bg-purple-100 text-purple-700",
  developer: "bg-blue-100 text-blue-700",
  viewer: "bg-slate-100 text-slate-600",
};

export default function UsersPage() {
  const { role: myRole, username: myUsername, isLoading } = useAuth();
  const router = useRouter();

  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [busyUserId, setBusyUserId] = useState<number | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<UserItem[]>("/auth/users");
      setUsers(res.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !myRole) {
      router.replace("/login");
      return;
    }
    if (!isLoading && myRole && myRole !== "admin") {
      router.replace("/dashboard");
      return;
    }
    if (myRole === "admin") fetchUsers();
  }, [myRole, isLoading, router, fetchUsers]);

  async function changeRole(user: UserItem, newRole: Role) {
    setBusyUserId(user.id);
    try {
      await api.patch(`/auth/users/${user.id}`, { role: newRole });
      await fetchUsers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to update role");
    } finally {
      setBusyUserId(null);
    }
  }

  async function toggleActive(user: UserItem) {
    setBusyUserId(user.id);
    try {
      await api.patch(`/auth/users/${user.id}`, { is_active: !user.is_active });
      await fetchUsers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to update user");
    } finally {
      setBusyUserId(null);
    }
  }

  async function deleteUser(user: UserItem) {
    if (!confirm(`Delete user "${user.username}"? This cannot be undone.`)) return;
    setBusyUserId(user.id);
    try {
      await api.delete(`/auth/users/${user.id}`);
      await fetchUsers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to delete user");
    } finally {
      setBusyUserId(null);
    }
  }

  if (myRole && myRole !== "admin") return null;

  return (
    <div className="min-h-screen">
      <Navbar crumbs={[{ label: "Users" }]} />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Users</h1>
            <p className="text-sm text-slate-500">
              Manage who can access the dashboard and what they can do.
            </p>
          </div>
          <button className="btn-primary" onClick={() => setShowAddModal(true)}>
            + Add User
          </button>
        </div>

        {loading && <p className="text-slate-500">Loading users…</p>}
        {error && <p className="text-red-600">{error}</p>}

        {!loading && !error && (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-left">
                <tr>
                  <th className="px-4 py-3 font-medium">Username</th>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => {
                  const isMe = u.username === myUsername;
                  const busy = busyUserId === u.id;
                  return (
                    <tr key={u.id}>
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {u.username} {isMe && <span className="text-xs text-slate-400">(you)</span>}
                      </td>
                      <td className="px-4 py-3 text-slate-500">{u.email || "—"}</td>
                      <td className="px-4 py-3">
                        <select
                          className={`badge border-0 ${ROLE_STYLES[u.role]} cursor-pointer`}
                          value={u.role}
                          disabled={busy}
                          onChange={(e) => changeRole(u, e.target.value as Role)}
                        >
                          <option value="viewer">viewer</option>
                          <option value="developer">developer</option>
                          <option value="admin">admin</option>
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`badge ${
                            u.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"
                          }`}
                        >
                          {u.is_active ? "active" : "disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-3">
                        <button
                          disabled={busy}
                          onClick={() => toggleActive(u)}
                          className="text-xs text-slate-500 hover:text-slate-800"
                        >
                          {u.is_active ? "Disable" : "Enable"}
                        </button>
                        {!isMe && (
                          <button
                            disabled={busy}
                            onClick={() => deleteUser(u)}
                            className="text-xs text-red-500 hover:text-red-700"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-6 text-xs text-slate-400 space-y-1">
          <p><span className="font-medium">Viewer</span> — read-only: can browse clients/servers/processes and view logs.</p>
          <p><span className="font-medium">Developer</span> — can also restart/stop/start PM2 processes.</p>
          <p><span className="font-medium">Admin</span> — full access: add/remove clients, servers, and manage users.</p>
        </div>
      </main>

      {showAddModal && <AddUserModal onClose={() => setShowAddModal(false)} onCreated={fetchUsers} />}
    </div>
  );
}
