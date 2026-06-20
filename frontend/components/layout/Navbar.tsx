"use client";
import { useRouter } from "next/navigation";

interface NavbarProps {
  jobId?: string;
  showDownload?: boolean;
  isComplete?: boolean;
  elapsed?: string;
}

export default function Navbar({ jobId, showDownload, isComplete, elapsed }: NavbarProps) {
  const router = useRouter();
  return (
    <nav style={{
      height: "52px",
      display: "flex", alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px",
      backgroundColor: "#080808",
      borderBottom: "1px solid #111",
      position: "sticky", top: 0, zIndex: 100,
      backdropFilter: "blur(8px)",
    }}>
      {/* Left: back + logo */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <button onClick={() => router.push("/")} style={{
          background: "none", border: "none", cursor: "pointer",
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "11px", color: "#333",
          display: "flex", alignItems: "center", gap: "6px",
          transition: "color 0.15s",
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = "#666"; }}
        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = "#333"; }}>
          ← Back
        </button>
        <span style={{ color: "#1a1a1a" }}>/</span>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={{
            width: "20px", height: "20px", background: "#f59e0b",
            borderRadius: "5px", display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: "11px", fontWeight: 700,
            color: "#000",
          }}>⚡</div>
          <span style={{
            fontFamily: "var(--font-syne), sans-serif",
            fontWeight: 700, fontSize: "13px", color: "#e0e0e0",
          }}>BrandForge</span>
        </div>
      </div>

      {/* Right: status + job ID */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {elapsed && !isComplete && (
          <span style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "11px", color: "#333",
          }}>
            {elapsed}
          </span>
        )}
        {jobId && (
          <span style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "#2a2a2a",
            letterSpacing: "1px",
          }}>
            {jobId.toUpperCase()}
          </span>
        )}
        {isComplete && (
          <span className="forge-badge" style={{
            animation: "forgeFadeIn 0.4s var(--forge-ease) both",
            color: "#10b981",
            background: "rgba(16,185,129,0.1)",
            borderColor: "rgba(16,185,129,0.25)",
          }}>
            ✓ Complete
          </span>
        )}
      </div>
    </nav>
  );
}
