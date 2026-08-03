"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface LogSource {
  id: number;
  server_id: number;
  label: string;
  remote_path: string;
  created_at: string;
}

interface LogFileEntry {
  name: string;
  size_bytes: number;
  modified: string | null;
  is_gz: boolean;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function lineColorClass(line: string): string {
  const match = line.match(/"level"\s*:\s*"(\w+)"/i);
  const level = (match ? match[1] : "").toLowerCase();
  if (level === "error" || level === "fatal") return "text-red-400";
  if (level === "warn" || level === "warning") return "text-yellow-400";
  return "text-green-400";
}

export default function ServerLogsBrowser({ serverId }: { serverId: number }) {
  const { role } = useAuth();
  const [sources, setSources] = useState<LogSource[]>([]);
  const [activeSourceId, setActiveSourceId] = useState<number | null>(null);
  const [files, setFiles] = useState<LogFileEntry[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tailLines, setTailLines] = useState<string[] | null>(null);
  const [tailFilename, setTailFilename] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [newPath, setNewPath] = useState("");

  const base = `/servers/${serverId}/logs`;
  const activeSourceLabel = sources.find((s) => s.id === activeSourceId)?.label || "Logs";

  const loadSources = async () => {
    try {
      const res = await api.get<LogSource[]>(`${base}/sources`);
      setSources(res.data);
      if (res.data.length && activeSourceId === null) {
        setActiveSourceId(res.data[0].id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load log sources");
    }
  };

  const loadFiles = async (sourceId: number) => {
    setLoadingFiles(true);
    setError(null);
    try {
      const res = await api.get<LogFileEntry[]>(`${base}/sources/${sourceId}/files`);
      setFiles(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load log files");
      setFiles([]);
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    loadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverId]);

  useEffect(() => {
    if (activeSourceId !== null) loadFiles(activeSourceId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSourceId]);

  const handleAddSource = async () => {
    if (!newLabel || !newPath) return;
    try {
      await api.post(`${base}/sources`, { label: newLabel, remote_path: newPath });
      setShowAddModal(false);
      setNewLabel("");
      setNewPath("");
      loadSources();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to add log path");
    }
  };

  const handleTail = async (filename: string) => {
    if (activeSourceId === null) return;
    setTailFilename(filename);
    setTailLines(["Loading…"]);
    setIsFullscreen(false);
    try {
      const res = await api.get(`${base}/sources/${activeSourceId}/files/${encodeURIComponent(filename)}/tail`, {
        params: { lines: 300 },
      });
      setTailLines(res.data.lines.length ? res.data.lines : ["(empty)"]);
    } catch (err: any) {
      setTailLines([err?.response?.data?.detail || "Failed to read file"]);
    }
  };

  const handleDownload = async (filename: string) => {
    if (activeSourceId === null) return;
    try {
      const res = await api.get(`${base}/sources/${activeSourceId}/files/${encodeURIComponent(filename)}/download`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError("Failed to download file");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-2 flex-wrap">
          {sources.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveSourceId(s.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                activeSourceId === s.id
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-700 border-slate-200"
              }`}
            >
              {s.label}
            </button>
          ))}
          {sources.length === 0 && (
            <span className="text-sm text-slate-400">No log paths configured yet.</span>
          )}
        </div>
        {role === "admin" && (
          <button onClick={() => setShowAddModal(true)} className="btn-secondary text-sm">
            + Add Log Path
          </button>
        )}
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      {activeSourceId !== null && (
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
            <span className="text-sm font-medium text-slate-500">
              Files (last 3 days)
            </span>
            <button
              className="text-xs text-slate-400 hover:text-slate-700"
              onClick={() => setActiveSourceId(null)}
            >
              Close
            </button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Size</th>
                <th className="px-4 py-2 font-medium">Modified</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loadingFiles && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-400">
                    Loading files…
                  </td>
                </tr>
              )}
              {!loadingFiles &&
                files.map((f) => (
                  <tr key={f.name} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-mono text-xs">{f.name}</td>
                    <td className="px-4 py-2">{formatBytes(f.size_bytes)}</td>
                    <td className="px-4 py-2 text-slate-500">{f.modified}</td>
                    <td className="px-4 py-2 space-x-3">
                      <button className="text-blue-600 hover:underline" onClick={() => handleTail(f.name)}>
                        View
                      </button>
                      <button className="text-blue-600 hover:underline" onClick={() => handleDownload(f.name)}>
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              {!loadingFiles && files.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-400">
                    No log files from the last 7 days.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tailFilename && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div
            className={`bg-slate-950 rounded-xl shadow-2xl flex flex-col ${
              isFullscreen ? "w-full h-full" : "w-full max-w-4xl max-h-[80vh]"
            }`}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <span className="text-white font-semibold text-sm">
                  {activeSourceLabel} — {tailFilename}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-green-900 text-green-300 text-xs">
                  last 300 lines
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  className="text-slate-400 hover:text-white text-xs"
                  onClick={() => setIsFullscreen((v) => !v)}
                  title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
                >
                  {isFullscreen ? "⤡" : "⤢"}
                </button>
                <button
                  className="text-slate-400 hover:text-white text-lg leading-none"
                  onClick={() => setTailFilename(null)}
                  title="Close"
                >
                  ×
                </button>
              </div>
            </div>
            <div className="p-4 overflow-auto flex-1 font-mono text-xs leading-relaxed">
              {tailLines?.map((line, i) => (
                <div key={i} className={`${lineColorClass(line)} whitespace-pre-wrap break-all`}>
                  {line}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md space-y-4">
            <h3 className="font-semibold text-lg">Add Log Path</h3>
            <input
              className="input-field text-sm w-full"
              placeholder="Label (e.g. App Logs)"
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
            />
            <input
              className="input-field text-sm w-full font-mono"
              placeholder="/var/www/backend/Production/integrations-node/logs"
              value={newPath}
              onChange={(e) => setNewPath(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <button className="btn-secondary text-sm" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button className="btn-primary text-sm" onClick={handleAddSource}>
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
