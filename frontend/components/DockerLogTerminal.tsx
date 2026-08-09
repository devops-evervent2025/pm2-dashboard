"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { WS_URL } from "@/lib/api";
import { getToken } from "@/lib/auth";

function logLineColorClass(line: string): string {
  const jsonMatch = line.match(/"level"\s*:\s*"([a-zA-Z]+)"/);
  const level = jsonMatch ? jsonMatch[1].toLowerCase() : null;
  if (level === "error" || level === "fatal" || level === "critical") return "text-red-400";
  if (level === "warn" || level === "warning") return "text-amber-400";
  if (level === "info" || level === "success") return "text-emerald-400";
  const lowered = line.toLowerCase();
  if (/\berror\b|\bfatal\b|\bexception\b|\bfailed\b/.test(lowered)) return "text-red-400";
  if (/\bwarn(ing)?\b/.test(lowered)) return "text-amber-400";
  if (/\bsuccess(ful(ly)?)?\b/.test(lowered)) return "text-emerald-400";
  return "text-slate-100";
}

export default function DockerLogTerminal({
  serverId,
  containerName,
}: {
  serverId: number;
  containerName: string;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error">("connecting");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [copied, setCopied] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setStatus("error");
      return;
    }
    const url = `${WS_URL}/ws/docker-logs/${serverId}/${encodeURIComponent(
      containerName
    )}?token=${encodeURIComponent(token)}`;
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
  }, [serverId, containerName]);

  useEffect(() => {
    if (!isAtBottom) return;
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight });
  }, [lines, isAtBottom]);

  const BOTTOM_THRESHOLD_PX = 60;
  function handleScroll() {
    const el = containerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsAtBottom(distanceFromBottom <= BOTTOM_THRESHOLD_PX);
  }
  function jumpToLatest() {
    setIsAtBottom(true);
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: "smooth" });
  }

  useEffect(() => {
    if (!isFullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  function handleClose() {
    wsRef.current?.close();
    router.back();
  }

  // Copies the RAW text of every line joined by newlines - never innerHTML,
  // never re-parsed as markup - so nothing a container prints can execute
  // or alter formatting when pasted elsewhere. React already escapes each
  // line for on-screen rendering; this copies the same plain strings.
  async function copyLogs() {
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error("Copy failed", err);
    }
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
        <span className="text-sm font-medium text-slate-700">{containerName} — live logs</span>
        <div className="flex items-center gap-2">
          <span className={`badge ${statusStyles[status]}`}>{status}</span>
          <button
            type="button"
            onClick={copyLogs}
            disabled={lines.length === 0}
            title="Copy logs"
            className="px-2 py-1 rounded text-xs font-medium hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors disabled:opacity-40"
          >
            {copied ? "Copied!" : "Copy logs"}
          </button>
          <button
            type="button"
            onClick={() => setIsFullscreen((v) => !v)}
            title={isFullscreen ? "Exit full screen" : "Full screen"}
            className="p-1.5 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            {isFullscreen ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8 3v3a2 2 0 0 1-2 2H3" />
                <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
                <path d="M3 16h3a2 2 0 0 1 2 2v3" />
                <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
              </svg>
            ) : (
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
      <div className="relative flex-1 min-h-0">
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto bg-slate-900 text-slate-100 font-mono text-xs p-4 space-y-0.5"
        >
          {lines.length === 0 && <p className="text-slate-500">Waiting for log output…</p>}
          {lines.map((line, i) => (
            <div key={i} className={`whitespace-pre-wrap break-all ${logLineColorClass(line)}`}>
              {line}
            </div>
          ))}
        </div>
        {!isAtBottom && (
          <button
            type="button"
            onClick={jumpToLatest}
            className="absolute bottom-3 right-3 px-3 py-1.5 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-100 text-xs font-medium shadow-lg flex items-center gap-1"
          >
            ↓ Jump to latest
          </button>
        )}
      </div>
    </div>
  );
}
