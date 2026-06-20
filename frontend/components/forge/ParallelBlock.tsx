"use client";
import AgentNode from "./AgentNode";
import type { AgentEvent } from "@/lib/sse";

interface Props {
  stages: Record<string, AgentEvent>;
}

const PARALLEL_AGENTS = [
  { key: "copywriter",   label: "copywriter_agent" },
  { key: "layout_agent", label: "layout_agent" },
  { key: "email_agent",  label: "email_agent" },
  { key: "ad_agent",     label: "ad_agent" },
];

export default function ParallelBlock({ stages }: Props) {
  return (
    <div style={{ position: "relative", border: "1px solid var(--forge-border-bright)", borderRadius: "var(--forge-radius)", padding: "12px", margin: "4px 0" }}>
      <span style={{
        position: "absolute", top: "-8px", left: "12px",
        background: "var(--forge-surface)", padding: "0 8px",
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: "9px", color: "var(--forge-amber)",
        letterSpacing: "1.5px", textTransform: "uppercase"
      }}>
        Parallel Fan-Out
      </span>
      <div style={{ display: "flex", flexDirection: "column", gap: "2px", marginTop: "4px" }}>
        {PARALLEL_AGENTS.map((a) => (
          <AgentNode
            key={a.key}
            label={a.label}
            stageKey={a.key}
            event={stages[a.key]}
            isParallel
          />
        ))}
      </div>
    </div>
  );
}