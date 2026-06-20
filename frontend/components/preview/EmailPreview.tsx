"use client";
import { useState } from "react";

export default function EmailPreview({ email }: { email: any }) {
  const [view, setView] = useState<"desktop" | "mobile">("desktop");
  
  return (
    <div className="forge-card" style={{ overflow: "hidden" }}>
      <div style={{
        background: "#0c0c0c", padding: "12px 20px", borderBottom: "1px solid #141414",
        display: "flex", justifyContent: "space-between", alignItems: "center"
      }}>
        <div>
          <span style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "var(--forge-amber)",
            textTransform: "uppercase", letterSpacing: "2px",
            display: "block", marginBottom: "4px",
          }}>{email.type} Email</span>
          <h3 style={{
            fontFamily: "var(--font-syne), sans-serif",
            fontWeight: 700, fontSize: "14px", color: "#ddd", margin: 0,
          }}>{email.headline || email.subject}</h3>
        </div>
        <div style={{ display: "flex", gap: "4px" }}>
          <button onClick={() => setView("desktop")} style={{
            fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px",
            padding: "4px 8px", background: view === "desktop" ? "var(--forge-elevated)" : "transparent",
            color: view === "desktop" ? "var(--forge-amber)" : "var(--forge-text-muted)",
            border: "1px solid", borderColor: view === "desktop" ? "var(--forge-amber)" : "var(--forge-border-bright)",
            borderRadius: "4px", cursor: "pointer"
          }}>Desktop</button>
          <button onClick={() => setView("mobile")} style={{
            fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px",
            padding: "4px 8px", background: view === "mobile" ? "var(--forge-elevated)" : "transparent",
            color: view === "mobile" ? "var(--forge-amber)" : "var(--forge-text-muted)",
            border: "1px solid", borderColor: view === "mobile" ? "var(--forge-amber)" : "var(--forge-border-bright)",
            borderRadius: "4px", cursor: "pointer"
          }}>Mobile</button>
        </div>
      </div>
      
      <div style={{ background: "#1a1a1a", padding: "24px", display: "flex", justifyContent: "center" }}>
        <div style={{
          width: view === "desktop" ? "100%" : "375px",
          maxWidth: "600px",
          background: "#fff",
          borderRadius: "8px",
          overflow: "hidden",
          transition: "width 0.3s var(--forge-ease)",
          boxShadow: "0 4px 24px rgba(0,0,0,0.2)"
        }}>
          <div style={{ borderBottom: "1px solid #eee", padding: "16px 24px" }}>
            <p style={{ fontFamily: "sans-serif", fontSize: "14px", color: "#333", margin: "0 0 4px 0" }}><strong>Subject:</strong> {email.subject}</p>
            {email.preview_text && <p style={{ fontFamily: "sans-serif", fontSize: "13px", color: "#666", margin: 0 }}>{email.preview_text}</p>}
          </div>
          <div style={{ padding: "24px" }}>
            <p style={{ fontFamily: "sans-serif", fontSize: "14px", color: "#333", lineHeight: 1.6, whiteSpace: "pre-wrap", margin: 0 }}>{email.body}</p>
            {email.cta_text && (
              <div style={{ marginTop: "24px", textAlign: "center" }}>
                <span style={{
                  display: "inline-block", fontFamily: "sans-serif", fontWeight: "bold",
                  fontSize: "14px", padding: "12px 24px", background: "#f59e0b",
                  borderRadius: "4px", color: "#fff",
                }}>{email.cta_text}</span>
              </div>
            )}
            {email.ps_line && (
              <p style={{ fontFamily: "sans-serif", fontSize: "13px", color: "#666", marginTop: "24px", fontStyle: "italic", margin: "24px 0 0 0" }}>P.S. {email.ps_line}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
