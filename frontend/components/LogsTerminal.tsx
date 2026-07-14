"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
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
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const router = useRouter();

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

  // Esc key exits fullscreen, same as most fullscreen UIs
  useEffect(() => {
    if (!isFullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  function handleClose() {
    // Explicitly close the socket ourselves (not just relying on unmount
    // cleanup) so the backend sees a clean disconnect immediately, then
    // navigate away. router.back() is used instead of a hardcoded path so
    // this keeps working regardless of how this page was reached.
    wsRef.current?.close();
    router.back();
  }

  const statusStyles: Record<string, string> = {
    connecting: "bg-amber-100 text-amber-700",
    open: "bg-emerald-100 text-emerald-700",
    closed: "bg-slate-200 text-slate-600",
    error: "bg-red-100 text-red-700",
  };

  return (
    <div
      className={
        isFullscreen
          ? "fixed inset-0 z-50 bg-white p-4 flex flex-col"
          : "card p-0 overflow-hidden flex flex-col h-[70vh]"
      }
    >
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50 rounded-t-lg">
        <span className="text-sm font-medium text-slate-700">{processName} — live logs</span>
        <div className="flex items-center gap-2">
          <span className={`badge ${statusStyles[status]}`}>{status}</span>
          <button
            type="button"
            onClick={() => setIsFullscreen((v) => !v)}
            title={isFullscreen ? "Exit full screen" : "Full screen"}
            className="p-1.5 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            {isFullscreen ? (
              // Minimize icon
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 3v3a2 2 0 0 1-2 2H3" />
                <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
                <path d="M3 16h3a2 2 0 0 1 2 2v3" />
                <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
              </svg>
            ) : (
              // Maximize icon
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 3H5a2 2 0 0 0-2 2v3" />
                <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
                <path d="M3 16v3a2 2 0 0 0 2 2h3" />
                <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
              </svg>
            )}
          </button>
          <button
            type="button"
            onClick={handleClose}
            title="Close logs"
            className="p-1.5 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>
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
