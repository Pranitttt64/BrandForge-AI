"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getResult, getDownloadUrl, type ForgeResult } from "@/lib/api";
import AssetTabs from "@/components/preview/AssetTabs";
import CopyVariants from "@/components/preview/CopyVariants";
import DownloadKit from "@/components/preview/DownloadKit";
import EmailPreview from "@/components/preview/EmailPreview";
import Navbar from "@/components/layout/Navbar";

interface Props {
  params: Promise<{ jobId: string }>;
}

type Tab = "copy" | "emails" | "ads" | "flyer" | "social";

export default function PreviewPage({ params }: Props) {
  const { jobId } = use(params) as { jobId: string };
  const router = useRouter();
  const [result, setResult] = useState<ForgeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("copy");

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const data = await getResult(jobId);
        if (data.status === "running") {
          setTimeout(fetchResult, 3000);
          return;
        }
        setResult(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load results.");
      } finally {
        setLoading(false);
      }
    };
    fetchResult();
  }, [jobId]);

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: "#0a0a0a",
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{
            width: "32px", height: "32px",
            border: "2px solid #1e1e1e", borderTopColor: "#f59e0b",
            borderRadius: "50%",
            animation: "forgeSpin 0.7s linear infinite",
            margin: "0 auto 16px",
          }} />
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "13px", color: "#444",
          }}>Loading brand kit...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: "#0a0a0a", padding: "24px",
      }}>
        <div style={{ maxWidth: "400px", textAlign: "center" }}>
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "13px", color: "#ef4444", marginBottom: "16px",
          }}>✗ {error || "No results found."}</p>
          <button
            onClick={() => router.push("/")}
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px", color: "#f59e0b",
              background: "none", border: "none", cursor: "pointer",
              borderBottom: "1px solid transparent",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderBottomColor = "#f59e0b"; }}
            onMouseLeave={e => { e.currentTarget.style.borderBottomColor = "transparent"; }}
          >
            ← Start over
          </button>
        </div>
      </div>
    );
  }

  const emails = result.email_output
    ? [
        { type: "Welcome",       key: "email_welcome",      ...result.email_output.email_welcome },
        { type: "Promotional",   key: "email_promo",        ...result.email_output.email_promo },
        { type: "Re-engagement", key: "email_reengagement", ...result.email_output.email_reengagement },
      ].filter((e) => e.subject || e.headline || e.body)
    : [];

  const ads = result.ad_output;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0a0a0a" }}>
      {/* Nav */}
      <Navbar jobId={jobId.slice(0, 8)} isComplete={true} />

      <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
        {/* Left sidebar — brand profile */}
        <div style={{
          width: "220px", flexShrink: 0,
          borderRight: "1px solid #141414",
          padding: "24px",
          background: "#0a0a0a",
          overflowY: "auto",
          height: "calc(100vh - 53px)",
          position: "sticky", top: "53px",
        }}>
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "#444",
            letterSpacing: "2px", textTransform: "uppercase",
            marginBottom: "16px",
          }}>Brand Profile</p>

          <h2 style={{
            fontFamily: "var(--font-syne), sans-serif",
            fontWeight: 900, fontSize: "20px",
            color: "#f0f0f0", marginBottom: "12px",
            letterSpacing: "-0.5px",
          }}>
            {result.brand_name || "Brand"}
          </h2>

          {/* Color swatches */}
          {result.brand_profile?.brand_colors && (
            <div style={{ marginBottom: "16px" }}>
              <p style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "10px", color: "#444",
                textTransform: "uppercase", letterSpacing: "1.5px",
                marginBottom: "8px",
              }}>
                Extracted Colors
              </p>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {Object.entries(
                  result.brand_profile.brand_colors as Record<string, string>
                )
                  .filter(([, hex]) => Boolean(hex))
                  .map(([role, hex]) => (
                    <div key={role} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <div
                        title={`${role}: ${hex}`}
                        style={{
                          width: "28px", height: "28px",
                          borderRadius: "50%",
                          backgroundColor: hex,
                          border: "1px solid #222",
                          cursor: "default",
                          transition: "transform 0.15s var(--forge-ease)",
                        }}
                        onMouseEnter={e => {
                          (e.currentTarget as HTMLDivElement).style.transform = "scale(1.2)";
                        }}
                        onMouseLeave={e => {
                          (e.currentTarget as HTMLDivElement).style.transform = "scale(1)";
                        }}
                      />
                      <span style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "8px", color: "#333",
                      }}>
                        {hex.toUpperCase()}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Meta fields */}
          {[
            { label: "Tone",      value: result.brand_tone },
            { label: "Category",  value: result.brand_category },
            { label: "Audience",  value: result.target_audience },
          ].map(({ label, value }) =>
            value ? (
              <div key={label} style={{ marginBottom: "12px" }}>
                <p style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "10px", color: "#444",
                  textTransform: "uppercase", letterSpacing: "1.5px",
                  marginBottom: "4px",
                }}>{label}</p>
                <p style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "11px", color: "#666",
                  lineHeight: 1.4,
                }}>{value}</p>
              </div>
            ) : null
          )}

          {/* USPs */}
          {result.usps && result.usps.length > 0 && (
            <div style={{ marginTop: "16px" }}>
              <p style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "10px", color: "#444",
                textTransform: "uppercase", letterSpacing: "1.5px",
                marginBottom: "8px",
              }}>USPs</p>
              {result.usps.slice(0, 3).map((usp, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", marginBottom: "6px" }}>
                  <div style={{ width: "4px", height: "4px", borderRadius: "50%", background: "#f59e0b", marginTop: "6px", flexShrink: 0 }} />
                  <p style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "11px", color: "#555", lineHeight: 1.4,
                  }}>{usp}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Main content */}
        <div style={{
          flex: 1, padding: "24px 32px",
          minWidth: 0, overflowY: "auto",
        }}>
          {/* Download bar */}
          <div style={{ marginBottom: "32px" }}>
            <DownloadKit jobId={jobId} brandName={result.brand_name} />
          </div>

          {/* Tabs */}
          <div style={{ marginBottom: "24px" }}>
            <AssetTabs active={activeTab} onChange={setActiveTab} />
          </div>

          {/* Tab content */}
          <div className="fade-in">

            {/* COPY VARIANTS */}
            {activeTab === "copy" && result.copy_output && (
              <CopyVariants copy={result.copy_output} />
            )}

            {/* EMAILS */}
            {activeTab === "emails" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                {emails.length === 0 ? (
                  <p style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "13px", color: "#444",
                  }}>No email data available.</p>
                ) : (
                  emails.map((email) => (
                    <EmailPreview key={email.key} email={email} />
                  ))
                )}
              </div>
            )}

            {/* AD COPY */}
            {activeTab === "ads" && ads && (
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                {ads.headlines && ads.headlines.length > 0 && (
                  <div>
                    <p style={{
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                      fontSize: "10px", color: "#444",
                      textTransform: "uppercase", letterSpacing: "2px",
                      marginBottom: "12px",
                    }}>Headlines</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      {ads.headlines.map((h, i) => (
                        <div key={i} style={{
                          display: "flex", alignItems: "center",
                          justifyContent: "space-between",
                          padding: "10px 0",
                          borderBottom: "1px solid #0e0e0e",
                        }}>
                          <p style={{
                            fontFamily: "var(--font-jetbrains-mono), monospace",
                            fontSize: "12px", color: "#888",
                          }}>{h}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {ads.hooks && ads.hooks.length > 0 && (
                  <div>
                    <p style={{
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                      fontSize: "10px", color: "#444",
                      textTransform: "uppercase", letterSpacing: "2px",
                      marginBottom: "12px",
                    }}>Scroll-Stopping Hooks</p>
                    {ads.hooks.map((h, i) => (
                      <div key={i} className="forge-card" style={{ padding: "16px", marginBottom: "8px" }}>
                        <p style={{
                          fontFamily: "var(--font-jetbrains-mono), monospace",
                          fontSize: "12px", color: "#777",
                        }}>{h}</p>
                      </div>
                    ))}
                  </div>
                )}

                {ads.google_rsa && (
                  <div>
                    <p style={{
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                      fontSize: "10px", color: "#444",
                      textTransform: "uppercase", letterSpacing: "2px",
                      marginBottom: "12px",
                    }}>Google RSA</p>
                    <div className="forge-card" style={{ padding: "16px" }}>
                      <p style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "10px", color: "#444",
                        textTransform: "uppercase", letterSpacing: "1px",
                        marginBottom: "8px",
                      }}>Headlines (max 30 chars)</p>
                      {ads.google_rsa.headlines?.map((h, i) => (
                        <p key={i} style={{
                          fontFamily: "var(--font-jetbrains-mono), monospace",
                          fontSize: "12px", color: "#777",
                          marginBottom: "4px",
                        }}>{h}</p>
                      ))}
                      <p style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "10px", color: "#444",
                        textTransform: "uppercase", letterSpacing: "1px",
                        marginBottom: "8px", marginTop: "16px",
                      }}>Descriptions (max 90 chars)</p>
                      {ads.google_rsa.descriptions?.map((d, i) => (
                        <p key={i} style={{
                          fontFamily: "var(--font-jetbrains-mono), monospace",
                          fontSize: "12px", color: "#777",
                          marginBottom: "4px",
                        }}>{d}</p>
                      ))}
                    </div>
                  </div>
                )}

                {ads.linkedin_ad && (
                  <div>
                    <p style={{
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                      fontSize: "10px", color: "#444",
                      textTransform: "uppercase", letterSpacing: "2px",
                      marginBottom: "12px",
                    }}>LinkedIn Ad</p>
                    <div className="forge-card" style={{ padding: "16px" }}>
                      {ads.linkedin_ad.intro && <p style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "12px", color: "#888",
                        fontWeight: 700, marginBottom: "8px",
                      }}>{ads.linkedin_ad.intro}</p>}
                      {ads.linkedin_ad.body && <p style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "12px", color: "#666",
                        lineHeight: 1.65,
                      }}>{ads.linkedin_ad.body}</p>}
                      {ads.linkedin_ad.cta && (
                        <p style={{
                          fontFamily: "var(--font-jetbrains-mono), monospace",
                          fontSize: "11px", color: "#f59e0b",
                          marginTop: "12px",
                        }}>{ads.linkedin_ad.cta} →</p>
                      )}
                    </div>
                  </div>
                )}

                {ads.meta_primary_text && (
                  <div>
                    <p style={{
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                      fontSize: "10px", color: "#444",
                      textTransform: "uppercase", letterSpacing: "2px",
                      marginBottom: "12px",
                    }}>Meta / Instagram Ad</p>
                    <div className="forge-card" style={{ padding: "16px" }}>
                      <p style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "12px", color: "#777",
                        lineHeight: 1.65,
                      }}>{ads.meta_primary_text}</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* FLYER */}
            {activeTab === "flyer" && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                <div className="forge-card" style={{
                  width: "100%", maxWidth: "520px",
                  overflow: "hidden",
                }}>
                  <iframe
                    src={`/api/forge/${jobId}/assets/flyer.pdf`}
                    style={{ width: "100%", height: "600px", border: "none" }}
                    title="Flyer PDF Preview"
                  />
                </div>
                <a
                  href={`/api/forge/${jobId}/assets/flyer.pdf`}
                  download="flyer.pdf"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "12px", color: "#f59e0b",
                    borderBottom: "1px solid transparent",
                    textDecoration: "none",
                    transition: "border-color 0.15s",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderBottomColor = "#f59e0b"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderBottomColor = "transparent"; }}
                >
                  ↓ Download flyer.pdf
                </a>
              </div>
            )}

            {/* SOCIAL CARD */}
            {activeTab === "social" && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                <div className="forge-card" style={{
                  width: "100%", maxWidth: "420px",
                  overflow: "hidden", padding: "8px",
                }}>
                  <img
                    src={`/api/forge/${jobId}/assets/social_card.png`}
                    alt="Social card preview"
                    style={{ width: "100%", borderRadius: "8px", display: "block" }}
                  />
                </div>
                <a
                  href={`/api/forge/${jobId}/assets/social_card.png`}
                  download="social_card.png"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "12px", color: "#f59e0b",
                    borderBottom: "1px solid transparent",
                    textDecoration: "none",
                    transition: "border-color 0.15s",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderBottomColor = "#f59e0b"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderBottomColor = "transparent"; }}
                >
                  ↓ Download social_card.png
                </a>
              </div>
            )}

          </div>
        </div>

        {/* Right sidebar — quick actions */}
        <div style={{
          width: "220px", flexShrink: 0,
          borderLeft: "1px solid #141414",
          padding: "24px",
          background: "#0a0a0a",
          overflowY: "auto",
          height: "calc(100vh - 53px)",
          position: "sticky", top: "53px",
        }}>
          <p style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "#444",
            letterSpacing: "2px", textTransform: "uppercase",
            marginBottom: "16px",
          }}>Quick Actions</p>

          <a
            href={getDownloadUrl(jobId)}
            download
            className="forge-btn-primary"
            style={{
              display: "block", textAlign: "center", padding: "10px 16px",
              fontSize: "12px", textDecoration: "none", marginBottom: "24px",
              borderRadius: "8px",
            }}
          >
            ↓ Download ZIP
          </a>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "32px" }}>
             <a href={`/api/forge/${jobId}/assets/flyer.pdf`} download="flyer.pdf" style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#f59e0b", textDecoration: "none" }}>↓ Flyer PDF</a>
             <a href={`/api/forge/${jobId}/assets/social_card.png`} download="social_card.png" style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#f59e0b", textDecoration: "none" }}>↓ Social Card</a>
             <a href={`/api/forge/${jobId}/assets/ad_copy.pdf`} download="ad_copy.pdf" style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#f59e0b", textDecoration: "none" }}>↓ Ad Copy</a>
             <a href={`/api/forge/${jobId}/assets/brand_profile.json`} download="brand_profile.json" style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#f59e0b", textDecoration: "none" }}>↓ Brand JSON</a>
          </div>

          <a href={`/?url=${encodeURIComponent(result.brand_url || "")}`} style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px",
            color: "#666", textDecoration: "none", transition: "color 0.15s"
          }} onMouseEnter={e => e.currentTarget.style.color = "#f0f0f0"} onMouseLeave={e => e.currentTarget.style.color = "#666"}>
            ⟳ Run again
          </a>
        </div>
      </div>
    </div>
  );
}