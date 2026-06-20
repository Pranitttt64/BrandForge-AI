"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { startForge } from "@/lib/api";

const URLS    = ["stripe.com","notion.so","linear.app","figma.com","vercel.com","loom.com"];
const AGENTS  = [
  "scraper_node","brand_extractor","rag_ingestor",
  "copywriter_agent","layout_agent","email_agent",
  "ad_agent","critic_agent","asset_generator","zip_packager",
];
const STATS = [
  { n: "10",   l: "AI Agents" },
  { n: "90s",  l: "Generate" },
  { n: "6",    l: "Asset types" },
  { n: "\u221e",    l: "Brands" },
];

export default function Hero() {
  const router = useRouter();
  const [url,           setUrl]           = useState("");
  const [loading,       setLoading]       = useState(false);
  const [validating,    setValidating]    = useState(false);
  const [error,         setError]         = useState<string|null>(null);
  const [phIdx,         setPhIdx]         = useState(0);
  const [activeAgent,   setActiveAgent]   = useState(0);
  const [inputFocused,  setInputFocused]  = useState(false);

  const sectionRef = useRef<HTMLElement>(null);
  const glowRef    = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);
  const rafRef     = useRef<number>(0);

  useEffect(() => {
    const el    = sectionRef.current;
    const glow  = glowRef.current;
    if (!el || !glow) return;
    const onMove = (e: MouseEvent) => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        glow.style.left    = `${e.clientX - r.left}px`;
        glow.style.top     = `${e.clientY - r.top}px`;
        glow.style.opacity = "1";
      });
    };
    const onLeave = () => { if (glow) glow.style.opacity = "0"; };
    el.addEventListener("mousemove", onMove, { passive: true });
    el.addEventListener("mouseleave", onLeave);
    return () => {
      el.removeEventListener("mousemove", onMove);
      el.removeEventListener("mouseleave", onLeave);
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  useEffect(() => {
    const t = setInterval(() => setPhIdx(i => (i+1) % URLS.length), 2600);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setActiveAgent(i => (i+1) % AGENTS.length), 720);
    return () => clearInterval(t);
  }, []);

  const handleSubmit = useCallback(async (raw: string) => {
    setError(null);
    let final = raw.trim();
    if (!final) { inputRef.current?.focus(); return; }
    if (!final.startsWith("http")) final = "https://" + final;
    try { new URL(final); } catch {
      setError("Please enter a valid URL."); return;
    }

    setValidating(true);
    try {
      const r = await fetch("/api/validate-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: final }),
      });
      const d = await r.json();
      if (!d.valid) {
        setError(d.error || "Cannot reach that URL.");
        setValidating(false);
        return;
      }
      final = d.url || final;
    } catch { /* proceed if validator unreachable */ }
    setValidating(false);

    setLoading(true);
    try {
      const jobId = await startForge(final);
      router.push(`/forge/${jobId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed. Try again.");
      setLoading(false);
    }
  }, [router]);

  const busy = loading || validating;

  return (
    <section
      ref={sectionRef}
      style={{
        position: "relative",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        backgroundColor: "#0a0a0a",
        paddingTop: "44px",
        paddingBottom: "80px",
        paddingLeft: "24px",
        paddingRight: "24px",
      }}
    >
      <div className="forge-grid" style={{ position: "absolute", inset: 0, pointerEvents: "none" }} />
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none", background: "radial-gradient(ellipse 80% 80% at 50% 50%, transparent 30%, #0a0a0a 100%)" }} />
      <div style={{ position: "absolute", top: "-8%", right: "-6%", width: "560px", height: "440px", pointerEvents: "none", background: "radial-gradient(ellipse, rgba(245,158,11,0.09) 0%, transparent 70%)", filter: "blur(48px)", animation: "forgeGlowPulse 5s ease-in-out infinite" }} />
      <div style={{ position: "absolute", bottom: "-6%", left: "-4%", width: "420px", height: "340px", pointerEvents: "none", background: "radial-gradient(ellipse, rgba(245,158,11,0.06) 0%, transparent 70%)", filter: "blur(56px)", animation: "forgeGlowPulse 7s ease-in-out infinite reverse" }} />
      <div ref={glowRef} style={{ position: "absolute", width: "600px", height: "600px", borderRadius: "50%", background: "radial-gradient(circle, rgba(245,158,11,0.07) 0%, transparent 65%)", transform: "translate(-50%, -50%)", pointerEvents: "none", transition: "opacity 0.5s ease", opacity: "0", filter: "blur(24px)", zIndex: 0 }} />

      {/* TICKER */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "36px", backgroundColor: "#080808", borderBottom: "1px solid #141414", display: "flex", alignItems: "center", overflow: "hidden", zIndex: 10 }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "60px", background: "linear-gradient(90deg, #080808, transparent)", zIndex: 2, pointerEvents: "none" }} />
        <div style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: "60px", background: "linear-gradient(-90deg, #080808, transparent)", zIndex: 2, pointerEvents: "none" }} />
        <div style={{ display: "flex", gap: "48px", whiteSpace: "nowrap", animation: "forgeMarquee 22s linear infinite", paddingLeft: "100%" }}>
          {[...AGENTS, ...AGENTS, ...AGENTS].map((a, i) => (
            <span key={i} style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", letterSpacing: "2.5px", textTransform: "uppercase", color: i % AGENTS.length === activeAgent ? "#f59e0b" : "#1e1e1e", transition: "color 0.4s ease", fontWeight: i % AGENTS.length === activeAgent ? 500 : 400 }}>{a}</span>
          ))}
        </div>
      </div>

      {/* CONTENT */}
      <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: "860px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
        <div className="slide-up" style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "36px" }}>
          <span style={{ height: "1px", width: "48px", display: "block", background: "linear-gradient(90deg, transparent, #f59e0b)" }} />
          <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#f59e0b", letterSpacing: "3.5px", textTransform: "uppercase" }}>Multi-Agent Brand Intelligence</span>
          <span style={{ height: "1px", width: "48px", display: "block", background: "linear-gradient(-90deg, transparent, #f59e0b)" }} />
        </div>

        <h1 className="slide-up delay-1" style={{ fontFamily: "var(--font-syne), system-ui, sans-serif", fontWeight: 900, fontSize: "clamp(48px, 8vw, 92px)", lineHeight: 1.0, letterSpacing: "-3px", color: "#f5f5f5", margin: "0 0 24px 0" }}>
          Turn any URL into a<br />
          <span style={{ color: "#f59e0b", textShadow: "0 0 120px rgba(245,158,11,0.4), 0 0 40px rgba(245,158,11,0.2)" }}>complete brand kit.</span>
        </h1>

        <p className="slide-up delay-2" style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "13px", color: "#444", lineHeight: 1.75, margin: "0 0 44px 0", maxWidth: "420px" }}>
          10 AI agents working in parallel.<br />Flyers · Emails · Social cards · Ad copy — all on-brand.
        </p>

        {/* INPUT */}
        <div className="slide-up delay-3" style={{ width: "100%", maxWidth: "620px", marginBottom: "14px" }}>
          <div style={{ padding: "1.5px", borderRadius: "14px", background: inputFocused ? "linear-gradient(135deg, rgba(245,158,11,0.75), rgba(245,158,11,0.1), rgba(245,158,11,0.45))" : "linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.03), rgba(245,158,11,0.1))", transition: "background 0.4s ease", boxShadow: inputFocused ? "0 0 48px rgba(245,158,11,0.14)" : "none" }}>
            <div style={{ display: "flex", background: "#0a0a0a", borderRadius: "12px", overflow: "hidden" }}>
              <input ref={inputRef} type="text" value={url} onChange={e => { setUrl(e.target.value); setError(null); }} onKeyDown={e => e.key === "Enter" && handleSubmit(url)} onFocus={() => setInputFocused(true)} onBlur={() => setInputFocused(false)} placeholder={`https://${URLS[phIdx]}`} disabled={busy} style={{ flex: 1, background: "transparent", border: "none", outline: "none", padding: "17px 20px", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "14px", color: "#e8e8e8", opacity: busy ? 0.5 : 1 }} />
              <button className="forge-btn-primary" onClick={() => handleSubmit(url)} disabled={busy || !url.trim()} style={{ margin: "7px", padding: "11px 24px", fontSize: "14px", letterSpacing: "-0.2px", display: "flex", alignItems: "center", gap: "8px", background: busy ? "#7a4e0a" : "linear-gradient(135deg, #f59e0b, #d97706)", boxShadow: busy ? "none" : "0 0 28px rgba(245,158,11,0.28)" }}>
                {busy && <span style={{ width: "13px", height: "13px", borderRadius: "50%", border: "2px solid rgba(0,0,0,0.3)", borderTopColor: "#000", display: "inline-block", animation: "forgeSpin 0.65s linear infinite" }} />}
                {validating ? "Checking\u2026" : loading ? "Starting\u2026" : "Forge Kit \u2192"}
              </button>
            </div>
          </div>

          {error && <p className="fade-in" style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#ef4444", marginTop: "10px", textAlign: "left" }}>✗ {error}</p>}

          <div style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "14px", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#2a2a2a" }}>
            <span>Try:</span>
            {URLS.slice(0,5).map(u => (
              <button key={u} onClick={() => { setUrl(`https://${u}`); setError(null); inputRef.current?.focus(); }} style={{ background: "none", border: "none", borderBottom: "1px solid transparent", cursor: "pointer", padding: "0", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#3a3a3a", transition: "color 0.15s, border-color 0.15s" }}
                onMouseEnter={e => { const el = e.currentTarget; el.style.color = "#f59e0b"; el.style.borderBottomColor = "#f59e0b"; }}
                onMouseLeave={e => { const el = e.currentTarget; el.style.color = "#3a3a3a"; el.style.borderBottomColor = "transparent"; }}>
                {u}
              </button>
            ))}
          </div>
        </div>

        {/* STATS */}
        <div className="slide-up delay-4" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", width: "100%", maxWidth: "620px", border: "1px solid #141414", borderRadius: "12px", overflow: "hidden", gap: "1px", background: "#141414", marginBottom: "18px" }}>
          {STATS.map((s, i) => (
            <div key={i} style={{ background: "#0a0a0a", padding: "18px 8px", display: "flex", flexDirection: "column", alignItems: "center", gap: "5px", cursor: "default", transition: "background 0.2s ease" }}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = "#0e0e0e"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = "#0a0a0a"; }}>
              <span style={{ fontFamily: "var(--font-syne), sans-serif", fontWeight: 900, fontSize: "24px", color: "#f59e0b", letterSpacing: "-0.5px", animation: `forgeCountUp 0.7s var(--forge-ease) ${0.7 + i*0.1}s both` }}>{s.n}</span>
              <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "9px", color: "#2a2a2a", textTransform: "uppercase", letterSpacing: "1.5px" }}>{s.l}</span>
            </div>
          ))}
        </div>

        {/* PILLS */}
        <div className="slide-up delay-5" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "6px", maxWidth: "620px" }}>
          {AGENTS.map((a, i) => (
            <div key={a} style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", padding: "5px 12px", borderRadius: "999px", border: `1px solid ${i === activeAgent ? "rgba(245,158,11,0.4)" : "#111"}`, color: i === activeAgent ? "#f59e0b" : "#1e1e1e", background: i === activeAgent ? "rgba(245,158,11,0.07)" : "transparent", boxShadow: i === activeAgent ? "0 0 16px rgba(245,158,11,0.1)" : "none", transition: "all 0.4s var(--forge-ease)", cursor: "default" }}>{a}</div>
          ))}
        </div>

        {/* SCROLL HINT */}
        <div className="slide-up delay-6" style={{ marginTop: "52px", display: "flex", flexDirection: "column", alignItems: "center", gap: "8px", animation: "forgeGlowPulse 3s ease-in-out infinite" }}>
          <div style={{ width: "1px", height: "40px", background: "linear-gradient(#f59e0b, transparent)" }} />
          <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "9px", color: "#2a2a2a", letterSpacing: "2px", textTransform: "uppercase" }}>scroll</span>
        </div>
      </div>
    </section>
  );
}