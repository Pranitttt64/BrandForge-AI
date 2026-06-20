"use client";
import { useEffect, useRef } from "react";

const STEPS = [
  {
    num: "01",
    title: "Scrape",
    desc: "Jina Reader + Playwright discovers and crawls your real pages \u2014 homepage, about, pricing, blog. Only pages that actually exist.",
    detail: "Concurrent fetching \u00b7 Real link discovery \u00b7 Jina fallback",
  },
  {
    num: "02",
    title: "Understand",
    desc: "RAG pipeline chunks and embeds all content into ChromaDB. 4 creative agents query it to know your brand deeply before writing a word.",
    detail: "ChromaDB \u00b7 all-MiniLM-L6-v2 \u00b7 Semantic search",
  },
  {
    num: "03",
    title: "Create",
    desc: "Copywriter, Layout, Email, and Ad agents run in parallel. A Critic agent reviews everything for tone and brand alignment.",
    detail: "LangGraph fan-out \u00b7 Groq llama-3.3-70b \u00b7 Parallel execution",
  },
  {
    num: "04",
    title: "Download",
    desc: "Flyer PDF, 1080\u00d71080 social card, 3 email templates, ad copy PDF \u2014 all in your brand colors, zipped and ready in seconds.",
    detail: "ReportLab \u00b7 Pillow \u00b7 ZIP bundle",
  },
];

export default function HowItWorks() {
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).style.opacity = "1";
            (entry.target as HTMLElement).style.transform = "translateY(0)";
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -60px 0px" }
    );

    cardsRef.current.forEach(card => {
      if (card) observer.observe(card);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <section style={{
      padding: "96px 24px",
      backgroundColor: "#0a0a0a",
      borderTop: "1px solid #0e0e0e",
    }}>
      <div style={{
        textAlign: "center", marginBottom: "56px",
      }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: "12px",
          marginBottom: "16px",
        }}>
          <span style={{ height: "1px", width: "32px", background: "linear-gradient(90deg, transparent, #f59e0b)", display: "block" }} />
          <span style={{
            fontFamily: "var(--font-jetbrains-mono), monospace",
            fontSize: "10px", color: "#f59e0b",
            letterSpacing: "3px", textTransform: "uppercase",
          }}>
            How It Works
          </span>
          <span style={{ height: "1px", width: "32px", background: "linear-gradient(-90deg, transparent, #f59e0b)", display: "block" }} />
        </div>
        <h2 style={{
          fontFamily: "var(--font-syne), system-ui, sans-serif",
          fontWeight: 800, fontSize: "clamp(28px, 4vw, 42px)",
          color: "#f0f0f0", letterSpacing: "-1px",
          margin: 0,
        }}>
          Four stages. One brand kit.
        </h2>
      </div>

      <div style={{
        maxWidth: "1100px", margin: "0 auto",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: "2px",
        backgroundColor: "#111",
        borderRadius: "16px",
        overflow: "hidden",
        border: "1px solid #141414",
      }}>
        {STEPS.map((step, i) => (
          <div
            key={step.num}
            ref={el => { cardsRef.current[i] = el; }}
            style={{
              backgroundColor: "#0a0a0a",
              padding: "32px 28px",
              position: "relative",
              cursor: "default",
              opacity: 0,
              transform: "translateY(24px)",
              transition: `opacity 0.65s var(--forge-ease) ${i*0.12}s,
                           transform 0.65s var(--forge-ease) ${i*0.12}s,
                           background-color 0.2s ease`,
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLDivElement).style.backgroundColor = "#0d0d0d";
              const accent = e.currentTarget.querySelector(".step-accent") as HTMLElement;
              if (accent) accent.style.width = "100%";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLDivElement).style.backgroundColor = "#0a0a0a";
              const accent = e.currentTarget.querySelector(".step-accent") as HTMLElement;
              if (accent) accent.style.width = "0%";
            }}
          >
            <div className="step-accent" style={{ position: "absolute", top: 0, left: 0, height: "2px", width: "0%", backgroundColor: "#f59e0b", transition: "width 0.4s var(--forge-ease)" }} />
            <div style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", color: "#f59e0b", letterSpacing: "2px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              {step.num}
              <span style={{ display: "inline-block", height: "1px", width: "20px", backgroundColor: "#f59e0b", opacity: 0.4 }} />
            </div>
            <h3 style={{ fontFamily: "var(--font-syne), system-ui, sans-serif", fontWeight: 700, fontSize: "20px", color: "#e8e8e8", margin: "0 0 12px 0", letterSpacing: "-0.3px" }}>{step.title}</h3>
            <p style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "12px", color: "#555", lineHeight: 1.65, margin: "0 0 20px 0" }}>{step.desc}</p>
            <div style={{ borderTop: "1px solid #161616", paddingTop: "14px" }}>
              <p style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", color: "#2a2a2a", lineHeight: 1.6, margin: 0 }}>{step.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}