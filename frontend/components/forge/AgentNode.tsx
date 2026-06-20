"use client";
import type { AgentEvent } from "@/lib/sse";

interface Props {
  label: string;
  stageKey: string;
  event?: AgentEvent;
  isParallel?: boolean;
}

const STATUS_CONFIG: Record<string, any> = {
  pending:   { dot: { background: "#333", width: "6px", height: "6px" }, text: "#444", badge: null },
  running:   { dot: { background: "#f59e0b", width: "8px", height: "8px", animation: "forgePulseAmber 1.8s infinite" }, text: "#f0f0f0", badge: { color: "#f59e0b", text: "⟳ running" } },
  progress:  { dot: { background: "#f59e0b", width: "8px", height: "8px", animation: "forgePulseAmber 1.8s infinite" }, text: "#f0f0f0", badge: { color: "#f59e0b", text: "⟳ running" } },
  started:   { dot: { background: "#f59e0b", width: "8px", height: "8px", animation: "forgePulseAmber 1.8s infinite" }, text: "#f0f0f0", badge: { color: "#f59e0b", text: "⟳ started" } },
  done:      { dot: { background: "#10b981", width: "6px", height: "6px" }, text: "#555", badge: { color: "#10b981", text: "✓" } },
  complete:  { dot: { background: "#10b981", width: "6px", height: "6px" }, text: "#555", badge: { color: "#10b981", text: "✓" } },
  success:   { dot: { background: "#10b981", width: "6px", height: "6px" }, text: "#555", badge: { color: "#10b981", text: "✓" } },
  warning:   { dot: { background: "#f59e0b", width: "6px", height: "6px" }, text: "#f59e0b", badge: { color: "#f59e0b", text: "⚠ warning" } },
  failed:    { dot: { background: "#ef4444", width: "8px", height: "8px" }, text: "#ef4444", badge: { color: "#ef4444", text: "✗" } },
};

export default function AgentNode({ label, stageKey, event, isParallel }: Props) {
  const status = event?.status ?? "pending";
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  const isRunning = status === "running" || status === "progress" || status === "started";
  const isDone = status === "done" || status === "complete" || status === "success";
  const isError = status === "failed";

  return (
    <div style={{
      position: "relative",
      display: "flex", alignItems: "center", gap: "12px",
      padding: "10px 12px", borderRadius: "var(--forge-radius)",
      transition: "all 0.3s var(--forge-ease)",
      background: isRunning ? "rgba(245,158,11,0.04)" : isError ? "rgba(239,68,68,0.04)" : "transparent",
      borderLeft: isRunning ? "2px solid rgba(245,158,11,0.3)" : isError ? "2px solid rgba(239,68,68,0.3)" : "2px solid transparent",
    }}>
      {isRunning && (
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(90deg, transparent 0%, rgba(245,158,11,0.03) 50%, transparent 100%)",
          backgroundSize: "200% 100%",
          animation: "forgeShimmer 2s infinite",
          borderRadius: "inherit",
          pointerEvents: "none",
        }} />
      )}
      <div style={{
        borderRadius: "50%",
        flexShrink: 0, ...cfg.dot,
        transition: "width 0.3s, height 0.3s, background 0.3s"
      }} />
      <span style={{
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: "12px", flex: 1,
        transition: "color 0.3s var(--forge-ease)",
        color: cfg.text, zIndex: 1
      }}>
        {label}
      </span>
      {cfg.badge && (
        <span style={{
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "10px", color: cfg.badge.color, zIndex: 1
        }}>
          {cfg.badge.text}
        </span>
      )}
    </div>
  );
}