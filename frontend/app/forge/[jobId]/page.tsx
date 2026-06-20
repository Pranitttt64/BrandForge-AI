"use client";
import { useEffect, use, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAgentStream } from "@/lib/sse";
import AgentTimeline from "@/components/forge/AgentTimeline";
import BrandProfile from "@/components/forge/BrandProfile";
import LiveLog from "@/components/forge/LiveLog";
import Navbar from "@/components/layout/Navbar";

interface Props {
  params: Promise<{ jobId: string }>;
}

function useElapsedTimer(running: boolean) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    if (!running) return;
    startRef.current = Date.now();
    const t = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(t);
  }, [running]);

  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

export default function ForgePage({ params }: Props) {
  const { jobId } = use(params) as { jobId: string };
  const router = useRouter();
  const { stages, brandProfile, isComplete, downloadUrl, error, logs, progress } =
    useAgentStream(jobId);

  const timer = useElapsedTimer(!isComplete && !error);
  const [countdown, setCountdown] = useState(3);

  useEffect(() => {
    if (isComplete) {
      const t = setInterval(() => {
        setCountdown((c) => Math.max(0, c - 1));
      }, 1000);
      return () => clearInterval(t);
    }
  }, [isComplete]);

  useEffect(() => {
    if (countdown === 0 && isComplete) {
      router.push(`/forge/${jobId}/preview`);
    }
  }, [countdown, isComplete, jobId, router]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0a0a0a" }}>
      {/* Nav */}
      <Navbar jobId={jobId.slice(0, 8)} isComplete={isComplete} elapsed={timer} />

      {/* Main content */}
      <div style={{ flex: 1, display: "flex", flexDirection: "row" }}>
        {/* Left: Agent Timeline — fixed width */}
        <div style={{
          width: "400px", flexShrink: 0,
          borderRight: "1px solid #141414",
          background: "#0c0c0c",
          padding: "24px",
          overflowY: "auto",
          height: "calc(100vh - 53px)",
          position: "sticky", top: "53px",
        }}>
          <AgentTimeline stages={stages} progress={progress} />
        </div>

        {/* Right: Brand Profile */}
        <div style={{
          flex: 1,
          padding: "24px",
          background: "#0a0a0a",
          overflowY: "auto",
          minWidth: 0,
        }}>
          {error ? (
            <div className="fade-in" style={{
              background: "#1a0a0a",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "12px",
              padding: "24px",
            }}>
              <p style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "11px", color: "#ef4444",
                textTransform: "uppercase", letterSpacing: "2px",
                marginBottom: "8px",
              }}>Pipeline Error</p>
              <p style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "13px", color: "#888",
              }}>{error}</p>
              <button
                onClick={() => router.push("/")}
                style={{
                  marginTop: "16px",
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "12px", color: "#f59e0b",
                  background: "none", border: "none",
                  cursor: "pointer", padding: 0,
                  borderBottom: "1px solid transparent",
                  transition: "border-color 0.15s",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderBottomColor = "#f59e0b"; }}
                onMouseLeave={e => { e.currentTarget.style.borderBottomColor = "transparent"; }}
              >
                ← Try again
              </button>
            </div>
          ) : brandProfile ? (
            <BrandProfile profile={brandProfile} />
          ) : (
            <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <p style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "10px", color: "#444",
                letterSpacing: "2px", textTransform: "uppercase",
              }}>
                Brand Intelligence
              </p>
              {/* Skeleton */}
              <div className="skeleton" style={{ height: "32px", width: "200px", borderRadius: "6px" }} />
              <div style={{ display: "flex", gap: "8px" }}>
                <div className="skeleton" style={{ height: "24px", width: "80px", borderRadius: "999px" }} />
                <div className="skeleton" style={{ height: "24px", width: "64px", borderRadius: "999px" }} />
              </div>
              <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="skeleton" style={{ width: "32px", height: "32px", borderRadius: "50%" }} />
                ))}
              </div>
              <div className="skeleton" style={{ height: "48px", borderRadius: "8px", marginTop: "8px" }} />
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
                {[1, 2, 3].map((i) => (
                  <div key={i} className="skeleton" style={{ height: "16px", borderRadius: "4px", width: `${80 - i * 10}%` }} />
                ))}
              </div>
              <p style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "11px", color: "#333",
                marginTop: "8px",
              }}>
                Analysing brand…
              </p>
            </div>
          )}

          {/* Complete notice */}
          {isComplete && (
            <div className="slide-up" style={{
              marginTop: "24px",
              background: "rgba(16,185,129,0.04)",
              border: "1px solid rgba(16,185,129,0.2)",
              borderRadius: "12px",
              padding: "16px 20px",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <div>
                <p style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "11px", color: "#10b981",
                  marginBottom: "4px",
                }}>Brand kit ready</p>
                <p style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "11px", color: "#555",
                }}>Redirecting to preview in {countdown}s…</p>
              </div>
              <button
                onClick={() => router.push(`/forge/${jobId}/preview`)}
                className="forge-btn-primary"
                style={{
                  padding: "10px 20px",
                  fontSize: "12px",
                }}
              >
                View Results →
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Live Log */}
      <LiveLog logs={logs} />
    </div>
  );
}