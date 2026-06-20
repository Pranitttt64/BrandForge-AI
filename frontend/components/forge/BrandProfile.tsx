"use client";
import type { BrandProfileData } from "@/lib/sse";

interface Props {
  profile: BrandProfileData;
}

export default function BrandProfile({ profile }: Props) {
  const colors = profile.colors;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", height: "100%" }}>
      <p className="slide-up delay-1" style={{
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: "10px", color: "var(--forge-text-muted)",
        letterSpacing: "2px", textTransform: "uppercase", margin: 0
      }}>
        Brand Intelligence
      </p>

      {/* Brand name + tone */}
      <div className="slide-up delay-2">
        <h2 style={{
          fontFamily: "var(--font-syne), sans-serif",
          fontSize: "24px", fontWeight: 900,
          color: "var(--forge-text-primary)", letterSpacing: "-1px",
          lineHeight: 1.1, margin: "0 0 12px 0"
        }}>
          {profile.brand_name || "—"}
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {profile.brand_tone && (
            <span className="forge-badge">
              {profile.brand_tone}
            </span>
          )}
          {profile.brand_category && (
            <span style={{
              display: "inline-flex", alignItems: "center", padding: "3px 10px",
              borderRadius: "999px", fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10px", letterSpacing: "1px", textTransform: "uppercase",
              background: "var(--forge-elevated)", color: "var(--forge-text-secondary)",
              border: "1px solid var(--forge-border-bright)"
            }}>
              {profile.brand_category}
            </span>
          )}
          {profile.brand_archetype && (
            <span style={{
              display: "inline-flex", alignItems: "center", padding: "3px 10px",
              borderRadius: "999px", fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10px", letterSpacing: "1px", textTransform: "uppercase",
              background: "var(--forge-elevated)", color: "var(--forge-text-secondary)",
              border: "1px solid var(--forge-border-bright)"
            }}>
              {profile.brand_archetype}
            </span>
          )}
        </div>
      </div>

      {/* Color palette */}
      {colors && Object.keys(colors).length > 0 && (
        <div className="slide-up delay-3">
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "var(--forge-text-muted)",
            letterSpacing: "1.5px", textTransform: "uppercase", margin: "0 0 12px 0"
          }}>
            Extracted Palette
          </p>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {Object.entries(colors).map(([role, hex]) =>
              hex ? (
                <div key={role} style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
                  <div style={{
                    width: "32px", height: "32px", borderRadius: "50%",
                    background: hex as string, border: "1px solid var(--forge-border-bright)",
                    cursor: "default", transition: "all 0.2s var(--forge-ease)",
                  }} onMouseEnter={e => {
                    e.currentTarget.style.transform = "scale(1.2)";
                    e.currentTarget.style.boxShadow = `0 0 16px ${hex}`;
                  }} onMouseLeave={e => {
                    e.currentTarget.style.transform = "scale(1)";
                    e.currentTarget.style.boxShadow = "none";
                  }} />
                  <span style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "8px", color: "var(--forge-text-muted)"
                  }}>
                    {hex as string}
                  </span>
                </div>
              ) : null
            )}
          </div>
        </div>
      )}

      {/* Audience */}
      {profile.target_audience && (
        <div className="slide-up delay-4">
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "var(--forge-text-muted)",
            letterSpacing: "1.5px", textTransform: "uppercase", margin: "0 0 6px 0"
          }}>Target Audience</p>
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "12px", color: "var(--forge-text-secondary)",
            lineHeight: 1.6, margin: 0
          }}>{profile.target_audience}</p>
        </div>
      )}

      {/* USPs */}
      {profile.usps && profile.usps.length > 0 && (
        <div>
          <p className="slide-up delay-4" style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "var(--forge-text-muted)",
            letterSpacing: "1.5px", textTransform: "uppercase", margin: "0 0 8px 0"
          }}>Unique Selling Props</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
            {profile.usps.map((usp, i) => (
              <li key={i} className="slide-up" style={{
                animationDelay: `${0.48 + i * 0.06}s`,
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "12px", color: "var(--forge-text-secondary)",
                display: "flex", alignItems: "flex-start", gap: "8px",
                lineHeight: 1.5
              }}>
                <span style={{ color: "var(--forge-amber)", marginTop: "1px" }}>&gt;</span>
                {usp}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Promise */}
      {profile.brand_promise && (
        <div className="slide-up" style={{ animationDelay: "0.8s" }}>
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "var(--forge-text-muted)",
            letterSpacing: "1.5px", textTransform: "uppercase", margin: "0 0 6px 0"
          }}>Brand Promise</p>
          <div style={{
            padding: "12px 16px", background: "var(--forge-elevated)",
            borderLeft: "2px solid var(--forge-amber)", borderRadius: "0 4px 4px 0",
          }}>
            <p style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px", color: "var(--forge-text-primary)",
              fontStyle: "italic", lineHeight: 1.6, margin: 0
            }}>&quot;{profile.brand_promise}&quot;</p>
          </div>
        </div>
      )}
    </div>
  );
}