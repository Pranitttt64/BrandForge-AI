"use client";
import { useState } from "react";
import type { CopyOutput } from "@/lib/api";

interface Props {
  copy: CopyOutput;
}

type Tone = "bold" | "friendly" | "professional";

function CopyLine({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", justifyContent: "space-between",
      gap: "12px", padding: "12px 0", borderBottom: "1px solid var(--forge-border-bright)"
    }} onMouseEnter={e => { (e.currentTarget.lastChild as HTMLElement).style.opacity = "1"; }}
       onMouseLeave={e => { (e.currentTarget.lastChild as HTMLElement).style.opacity = "0.4"; }}>
      <p style={{
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: "12px", color: "var(--forge-text-secondary)",
        lineHeight: 1.6, flex: 1, margin: 0
      }}>{text}</p>
      <button
        onClick={handleCopy}
        style={{
          flexShrink: 0, fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "10px", padding: "4px 8px", border: "1px solid var(--forge-border-bright)",
          borderRadius: "4px", background: "none", color: "var(--forge-text-muted)",
          cursor: "pointer", transition: "all 0.15s var(--forge-ease)", opacity: 0.4
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = "var(--forge-text-secondary)";
          e.currentTarget.style.color = "var(--forge-text-primary)";
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = "var(--forge-border-bright)";
          e.currentTarget.style.color = "var(--forge-text-muted)";
        }}
      >
        {copied ? "✓ copied" : "copy"}
      </button>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div style={{ marginBottom: "24px" }}>
      <p style={{
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: "10px", color: "var(--forge-text-muted)",
        letterSpacing: "2px", textTransform: "uppercase", marginBottom: "8px"
      }}>{title}</p>
      {items.map((item, i) => <CopyLine key={i} text={item} />)}
    </div>
  );
}

export default function CopyVariants({ copy }: Props) {
  const [tone, setTone] = useState<Tone>("bold");

  const headlines    = copy.headlines?.[tone] ?? [];
  const heroText     = copy.hero_text?.[tone] ? [copy.hero_text[tone]!] : [];
  const subheadlines = copy.subheadlines?.[tone] ?? [];
  const valueProps   = copy.value_props?.[tone] ?? [];
  const ctas         = copy.call_to_actions?.[tone] ?? [];

  return (
    <div className="fade-in">
      {/* Tone switcher */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        {(["bold", "friendly", "professional"] as Tone[]).map((t) => {
          const isActive = tone === t;
          return (
            <button
              key={t}
              onClick={() => setTone(t)}
              style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "10px", padding: "6px 12px",
                borderRadius: "999px", border: "1px solid",
                transition: "all 0.15s var(--forge-ease)", textTransform: "capitalize",
                background: isActive ? "var(--forge-elevated)" : "transparent",
                borderColor: isActive ? "var(--forge-amber)" : "var(--forge-border-bright)",
                color: isActive ? "var(--forge-amber)" : "var(--forge-text-muted)",
                cursor: "pointer", outline: "none",
              }}
              onMouseEnter={e => {
                if (!isActive) {
                  e.currentTarget.style.borderColor = "var(--forge-text-muted)";
                  e.currentTarget.style.color = "var(--forge-text-secondary)";
                }
              }}
              onMouseLeave={e => {
                if (!isActive) {
                  e.currentTarget.style.borderColor = "var(--forge-border-bright)";
                  e.currentTarget.style.color = "var(--forge-text-muted)";
                }
              }}
            >
              {t}
            </button>
          );
        })}
      </div>

      <Section title="Headlines" items={headlines} />
      <Section title="Hero Text" items={heroText} />
      <Section title="Subheadlines" items={subheadlines} />
      <Section title="Value Props" items={valueProps} />
      <Section title="Calls to Action" items={ctas} />
    </div>
  );
}