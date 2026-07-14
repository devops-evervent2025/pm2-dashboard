"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function LogsTerminal({
  serverId,
  processName,
}: {
  serverId: number;
  processName: string;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error">("connecting");
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setStatus("error");
      return;
    }

    const url = `${WS_URL}/ws/logs/${serverId}/${encodeURIComponent(processName)}?token=${encodeURIComponent(
      token
    )}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus("open");
    ws.onmessage = (event) => {
      const data: string = event.data;
      if (data === "__PING__") return;
      if (data === "__STREAM_CLOSED__") {
        setStatus("closed");
        return;
      }
      if (data.startsWith("__ERROR__")) {
        setLines((prev) => [...prev, `⚠ ${data.replace("__ERROR__:", "").replace("__ERROR__", "")}`]);
        setStatus("error");
        return;
      }
      setLines((prev) => {
        const next = [...prev, data];
        return next.length > 2000 ? next.slice(next.length - 2000) : next;
      });
    };
    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus((prev) => (prev === "error" ? prev : "closed"));

    return () => {
      ws.close();
    };
  }, [serverId, processName]);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [lines]);

  const statusStyles: Record<string, string> = {
    connecting: "bg-amber-100 text-amber-700",
    open: "bg-emerald-100 text-emerald-700",
    closed: "bg-slate-200 text-slate-600",
    error: "bg-red-100 text-red-700",
  };

  return (
    <div className="card p-0 overflow-hidden flex flex-col h-[70vh]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50">
        <span className="text-sm font-medium text-slate-700">{processName} — live logs</span>
        <span className={`badge ${statusStyles[status]}`}>{status}</span>
      </div>
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto bg-slate-900 text-slate-100 font-mono text-xs p-4 space-y-0.5"
      >
        {lines.length === 0 && (
          <p className="text-slate-500">Waiting for log output…</p>
        )}
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all">
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}
