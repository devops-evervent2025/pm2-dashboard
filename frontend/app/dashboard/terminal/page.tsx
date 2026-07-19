"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import { api, ServerItem } from "@/lib/api";

interface HistoryEntry {
  id: string;
  command: string;
  stdout: string;
  stderr: string;
  exit_status: number | null;
  error?: string;
  ranAt: string;
}

function tryPrettyPrint(text: string): { pretty: string | null; isJson: boolean } {
  const trimmed = text.trim();
  if (!trimmed) return { pretty: null, isJson: false };
  try {
    const parsed = JSON.parse(trimmed);
    return { pretty: JSON.stringify(parsed, null, 2), isJson: true };
  } catch {
    return { pretty: null, isJson: false };
  }
}

export default function ServerTerminalPage() {
  const { role, isLoading } = useAuth();
  const router = useRouter();

  const [servers, setServers] = useState<ServerItem[]>([]);
  const [serverId, setServerId] = useState<number | "">("");
  const [command, setCommand] = useState("");
  const [running, setRunning] = useState(false);
  const [latest, setLatest] = useState<HistoryEntry | null>(null);
  const [beautified, setBeautified] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!isLoading && !role) {
      router.replace("/login");
    }
  }, [role, isLoading, router]);

  const loadServers = useCallback(async () => {
    try {
      const res = await api.get<ServerItem[]>("/servers");
      setServers(res.data);
    } catch {
      setLoadError("Could not load servers.");
    }
  }, []);

  useEffect(() => {
    if (role) loadServers();
  }, [role, loadServers]);

  const runCommand = async () => {
    if (!serverId || !command.trim() || running) return;
    setRunning(true);
    const ranAt = new Date().toLocaleTimeString();
    try {
      const res = await api.post(`/servers/${serverId}/terminal`, { command });
      setBeautified(false);
      setLatest({
        id: `${Date.now()}`,
        command,
        stdout: res.data.stdout || "",
        stderr: res.data.stderr || "",
        exit_status: res.data.exit_status,
        ranAt,
      });
      setCommand("");
    } catch (err: any) {
      setBeautified(false);
      setLatest({
        id: `${Date.now()}`,
        command,
        stdout: "",
        stderr: "",
        exit_status: null,
        error: err?.response?.data?.detail || "Command failed.",
        ranAt,
      });
    } finally {
      setRunning(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runCommand();
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-semibold text-slate-800 mb-2">Server Terminal</h1>
        <p className="text-sm text-slate-500 mb-6">
          Run curl commands against a managed server over its existing SSH connection.
          Only plain curl commands are allowed - no downloading files, and no commands
          copied from a browser's "Copy as cURL" (those carry session cookies).
          Every command run here is logged.
        </p>

        <div className="card p-6 mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1">Server</label>
          <select
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-4"
            value={serverId}
            onChange={(e) => setServerId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select a server...</option>
            {servers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.ip_address})
              </option>
            ))}
          </select>
          {loadError && <p className="text-sm text-red-600 mb-3">{loadError}</p>}

          <label className="block text-sm font-medium text-slate-700 mb-1">Command</label>
          <textarea
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono mb-3"
            rows={2}
            placeholder='curl -s https://example.com/health'
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={!serverId}
          />
          <button
            onClick={runCommand}
            disabled={!serverId || !command.trim() || running}
            className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? "Running..." : "Run"}
          </button>
          <span className="text-xs text-slate-400 ml-3">Enter to run, Shift+Enter for a new line</span>
        </div>

        <div className="space-y-4">
          {!latest && (
            <p className="text-sm text-slate-400">No command run yet this session.</p>
          )}
          {latest && (() => {
            const h = latest;
            return (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <code className="text-xs text-slate-500">{h.ranAt}</code>
                {h.exit_status !== null && h.exit_status !== undefined && (
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      h.exit_status === 0
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    exit {h.exit_status}
                  </span>
                )}
              </div>
              <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs overflow-x-auto mb-2">
                $ {h.command}
              </pre>
              {h.error && <p className="text-sm text-red-600">{h.error}</p>}
              {h.stdout && (() => {
                const { pretty, isJson } = tryPrettyPrint(h.stdout);
                const isBeautified = beautified;
                const displayText = isJson && isBeautified && pretty ? pretty : h.stdout;
                return (
                  <div className="mb-2">
                    {isJson && (
                      <div className="flex justify-end mb-1">
                        <button
                          onClick={() =>
                            setBeautified((prev) => !prev)
                          }
                          className="text-xs px-2 py-1 rounded-md bg-slate-700 text-slate-100 hover:bg-slate-600"
                        >
                          {isBeautified ? "Show raw" : "Beautify"}
                        </button>
                      </div>
                    )}
                    <pre className="bg-slate-950 text-green-300 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap">
                      {displayText}
                    </pre>
                  </div>
                );
              })()}
              {h.stderr && (
                <pre className="bg-slate-950 text-red-300 rounded-lg p-3 text-xs overflow-x-auto whitespace-pre-wrap">
                  {h.stderr}
                </pre>
              )}
            </div>
            );
          })()}
        </div>
      </main>
    </div>
  );
}
