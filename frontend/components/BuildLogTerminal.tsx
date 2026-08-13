"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useLogAutoScroll } from "@/lib/useLogAutoScroll";

// Strips ANSI/VT100 escape + cursor-control sequences (used by npm,
// prisma, etc. for progress bars/spinners) - without this, raw control
// codes like "\x1b[1G\x1b[0K" show up as literal "[1G [0K" text since
// this is a plain <pre>, not a real terminal emulator.
// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /[\u001B\u009B][[\]()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-PR-TZcf-ntqry=><~]/g;

function stripAnsi(line: string): string {
  return line.replace(ANSI_REGEX, "");
}

function lineColorClass(line: string): string {
  const lowered = line.toLowerCase();
  if (line.startsWith("__ERROR__") || /\berror\b|\bfailed\b|\bfatal\b/.test(lowered)) {
    return "text-red-400";
  }
  if (/restarting pm2 process|restarted\.?$/.test(lowered)) {
    return "text-emerald-400";
  }
  if (/expected branch|build finished/.test(lowered)) {
    return "text-sky-400";
  }
  return "text-slate-100";
}

type Status = "connecting" | "open" | "closed" | "error";

export default function BuildLogTerminal({
  wsPath,
  title,
  onClose,
  onStatusChange,
}: {
  wsPath: string;
  title: string;
  onClose?: () => void;
  onStatusChange?: (status: Status, hadError: boolean) => void;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const { containerRef, isAtBottom, jumpToLatest, scrollHandlers } = useLogAutoScroll(lines);
  const [status, setStatus] = useState<Status>("connecting");
  const [errored, setErrored] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setStatus("error");
      return;
    }

    const url = `${WS_URL}${wsPath}?token=${encodeURIComponent(token)}`;
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
        setErrored(true);
      }
      setLines((prev) => [...prev, data]);
    };
    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus((prev) => (prev === "error" ? prev : "closed"));

    return () => {
      ws.close();
    };
  }, [wsPath]);


  useEffect(() => {
    onStatusChange?.(status, errored);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, errored]);

  const statusStyles: Record<string, string> = {
    connecting: "bg-amber-100 text-amber-700",
    open: "bg-emerald-100 text-emerald-700",
    closed: "bg-slate-200 text-slate-600",
    error: "bg-red-100 text-red-700",
  };

  return (
    <div className="card p-0 overflow-hidden flex flex-col h-[70vh]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50 rounded-t-lg">
        <span className="text-sm font-medium text-slate-700">{title} — build &amp; restart</span>
        <div className="flex items-center gap-2">
          <span className={`badge ${statusStyles[status]}`}>{status}</span>
          {onClose && (
            <button
              type="button"
              onClick={() => {
                wsRef.current?.close();
                onClose();
              }}
              title="Close"
              className="p-1.5 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
      <div className="relative flex-1 min-h-0">
        <div ref={containerRef} {...scrollHandlers} className="h-full overflow-y-auto bg-slate-900 text-slate-100 font-mono text-xs p-4 space-y-0.5">
        {lines.length === 0 && <p className="text-slate-500">Connecting…</p>}
        {lines.map((line, i) => {
          const cleaned = stripAnsi(line);
          if (!cleaned.trim()) return null;  // skip now-empty progress-bar/spinner noise
          return (
            <div key={i} className={`whitespace-pre-wrap break-all ${lineColorClass(cleaned)}`}>
              {cleaned}
            </div>
          );
        })}
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
