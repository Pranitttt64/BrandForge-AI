"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  logs: string[];
}

export default function LiveLog({ logs }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!collapsed) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, collapsed]);

  return (
    <div style={{ borderTop: "1px solid var(--forge-border)" }}>
      <button
        onClick={() => setCollapsed((c) => !c)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 20px", background: "none", border: "none", cursor: "pointer",
          fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px",
          color: "var(--forge-text-muted)", letterSpacing: "2px", textTransform: "uppercase",
          transition: "color 0.15s"
        }}
        onMouseEnter={e => { e.currentTarget.style.color = "var(--forge-text-secondary)"; }}
        onMouseLeave={e => { e.currentTarget.style.color = "var(--forge-text-muted)"; }}
      >
        <span>Terminal Log ({logs.length} events)</span>
        <span>{collapsed ? "▲ expand" : "▼ collapse"}</span>
      </button>

      {!collapsed && (
        <div style={{
          background: "#070707", padding: "8px 20px 16px 20px",
          maxHeight: "120px", overflowY: "auto",
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "11px", lineHeight: 1.6
        }}>
          {logs.length === 0 ? (
            <p style={{ color: "var(--forge-border-bright)", margin: 0 }}>Waiting for events...</p>
          ) : (
            logs.map((line, i) => {
              let color = "var(--forge-text-muted)";
              if (line.includes("✗") || line.includes("ERROR")) color = "var(--forge-error)";
              else if (line.includes("✓")) color = "var(--forge-success)";
              else if (line.includes("⚠")) color = "var(--forge-warning)";
              
              return (
                <p key={i} style={{ color, margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                  <span style={{ color: "var(--forge-amber)", marginRight: "4px" }}>&gt;</span>
                  {line}
                </p>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}