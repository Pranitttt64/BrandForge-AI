"use client";
import { useState } from "react";
import { getDownloadUrl } from "@/lib/api";

interface Props {
  jobId: string;
  brandName?: string;
}

export default function DownloadKit({ jobId, brandName }: Props) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = () => {
    setDownloading(true);
    const a = document.createElement("a");
    a.href = getDownloadUrl(jobId);
    a.download = `brandforge_kit_${brandName ?? jobId}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => setDownloading(false), 2000);
  };

  return (
    <div style={{
      background: "var(--forge-surface)", border: "1px solid var(--forge-border)",
      borderRadius: "var(--forge-radius-xl)", padding: "20px",
      display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px"
    }}>
      <div>
        <p style={{
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "11px", color: "var(--forge-amber)", margin: "0 0 4px 0"
        }}>Brand Kit Ready</p>
        <p style={{
          fontFamily: "var(--font-jetbrains-mono), monospace",
          fontSize: "11px", color: "var(--forge-text-muted)", margin: 0
        }}>
          flyer.pdf · social_card.png · 3 emails · ad_copy.pdf · brand_profile.json
        </p>
      </div>
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="forge-btn-primary"
        style={{
          flexShrink: 0, display: "flex", alignItems: "center", gap: "8px",
          padding: "12px 20px", fontSize: "14px", whiteSpace: "nowrap"
        }}
      >
        {downloading ? (
          <>
            <span style={{
              width: "14px", height: "14px", border: "2px solid rgba(0,0,0,0.3)",
              borderTopColor: "#000", borderRadius: "50%",
              animation: "forgeSpin 0.65s linear infinite"
            }} />
            Downloading...
          </>
        ) : (
          "↓ Download ZIP"
        )}
      </button>
    </div>
  );
}