"use client";
import AgentNode from "./AgentNode";
import ParallelBlock from "./ParallelBlock";
import type { AgentEvent } from "@/lib/sse";

interface Props {
  stages: Record<string, AgentEvent>;
  progress: number;
}

export default function AgentTimeline({ stages, progress }: Props) {
  const activeAgents = Object.values(stages).filter(
    s => s.status === "running" || s.status === "progress" || s.status === "started"
  ).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <p style={{
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "10px", color: "var(--forge-text-muted)",
          letterSpacing: "2px", textTransform: "uppercase", margin: 0
        }}>
          Agent Pipeline
        </p>
        {activeAgents > 0 && (
          <span style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "9px", color: "var(--forge-amber)",
            background: "rgba(245,158,11,0.1)", padding: "2px 6px",
            borderRadius: "4px", border: "1px solid rgba(245,158,11,0.2)"
          }}>
            {activeAgents} active
          </span>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "2px", flex: 1 }}>
        <AgentNode label="scraper_node"      stageKey="scraper"         event={stages["scraper"]} />
        <AgentNode label="brand_extractor"   stageKey="brand_extractor" event={stages["brand_extractor"]} />
        <AgentNode label="rag_ingestor"      stageKey="rag_ingestor"    event={stages["rag_ingestor"]} />
        <ParallelBlock stages={stages} />
        <AgentNode label="critic_agent"      stageKey="critic"          event={stages["critic"]} />
        <AgentNode label="asset_generator"   stageKey="asset_generator" event={stages["asset_generator"]} />
        <AgentNode label="zip_packager"      stageKey="zip_packager"    event={stages["zip_packager"]} />
      </div>

      <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--forge-border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
          <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", color: "var(--forge-text-secondary)" }}>
            Overall progress
          </span>
          <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", color: "var(--forge-amber)" }}>
            {progress}%
          </span>
        </div>
        <div style={{
          height: "3px", background: "#111",
          borderRadius: "2px", overflow: "hidden",
        }}>
          <div style={{
            height: "100%",
            width: `${progress}%`,
            background: "linear-gradient(90deg, #d97706, #f59e0b)",
            borderRadius: "2px",
            transition: "width 0.8s var(--forge-ease)",
            boxShadow: progress > 0 ? "0 0 12px rgba(245,158,11,0.4)" : "none",
          }} />
        </div>
      </div>
    </div>
  );
}