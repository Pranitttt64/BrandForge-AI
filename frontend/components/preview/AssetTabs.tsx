"use client";

type Tab = "copy" | "emails" | "ads" | "flyer" | "social";

interface Props {
  active: Tab;
  onChange: (t: Tab) => void;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "copy",   label: "Copy Variants" },
  { id: "emails", label: "Emails" },
  { id: "ads",    label: "Ad Copy" },
  { id: "flyer",  label: "Flyer PDF" },
  { id: "social", label: "Social Card" },
];

export default function AssetTabs({ active, onChange }: Props) {
  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
      {TABS.map((t) => {
        const isActive = active === t.id;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "11px", padding: "6px 16px",
              borderRadius: "999px", border: "1px solid",
              transition: "all 0.15s var(--forge-ease)",
              background: isActive ? "rgba(245,158,11,0.08)" : "transparent",
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
            {t.label}
          </button>
        );
      })}
    </div>
  );
}