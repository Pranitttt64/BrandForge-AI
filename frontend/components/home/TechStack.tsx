"use client";
import { useEffect, useRef } from "react";

const TECH = [
  { name: "LangGraph",         role: "Agent orchestration",    color: "#10b981" },
  { name: "ChromaDB",          role: "Vector store",           color: "#f59e0b" },
  { name: "Groq API",          role: "LLM inference",          color: "#8b5cf6" },
  { name: "Jina Reader",       role: "Web scraping",           color: "#3b82f6" },
  { name: "Sentence-Transformers", role: "Embeddings",         color: "#ef4444" },
  { name: "FastAPI",           role: "Backend API",            color: "#10b981" },
  { name: "Next.js 14",        role: "Frontend framework",     color: "#f0f0f0" },
  { name: "Playwright",        role: "Browser automation",     color: "#f59e0b" },
  { name: "ReportLab",         role: "PDF generation",         color: "#8b5cf6" },
  { name: "Pillow",            role: "Image generation",       color: "#3b82f6" },
  { name: "SSE Streaming",     role: "Real-time events",       color: "#ef4444" },
  { name: "RAG Pipeline",      role: "Knowledge retrieval",    color: "#10b981" },
];

export default function TechStack() {
  const itemsRef = useRef<(HTMLDivElement|null)[]>([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) {
          (e.target as HTMLElement).style.opacity = "1";
          (e.target as HTMLElement).style.transform = "translateY(0) scale(1)";
        }
      }),
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    itemsRef.current.forEach(el => { if (el) observer.observe(el); });
    return () => observer.disconnect();
  }, []);

  return (
    <section style={{
      padding: "96px 24px",
      backgroundColor: "#0a0a0a",
      borderTop: "1px solid #0e0e0e",
    }}>
      <div style={{ maxWidth: "960px", margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: "56px" }}>
          <div style={{
            display: "inline-flex", alignItems: "center",
            gap: "12px", marginBottom: "16px",
          }}>
            <span style={{ height: "1px", width: "32px", background: "linear-gradient(90deg, transparent, #f59e0b)", display: "block" }} />
            <span style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10px", color: "#f59e0b",
              letterSpacing: "3px", textTransform: "uppercase",
            }}>
              Technology
            </span>
            <span style={{ height: "1px", width: "32px", background: "linear-gradient(-90deg, transparent, #f59e0b)", display: "block" }} />
          </div>
          <h2 style={{
            fontFamily: "var(--font-syne), sans-serif",
            fontWeight: 800, fontSize: "clamp(26px, 4vw, 40px)",
            color: "#f0f0f0", letterSpacing: "-1px", margin: 0,
          }}>
            All free. All powerful.
          </h2>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "2px", background: "#111",
          borderRadius: "16px", overflow: "hidden",
          border: "1px solid #141414",
        }}>
          {TECH.map((t, i) => (
            <div
              key={t.name}
              ref={el => { itemsRef.current[i] = el; }}
              style={{
                background: "#0a0a0a", padding: "24px 20px",
                cursor: "default", opacity: 0,
                transform: "translateY(16px) scale(0.97)",
                transition: `opacity 0.55s var(--forge-ease) ${i * 0.055}s, transform 0.55s var(--forge-ease) ${i * 0.055}s, background 0.2s ease, border-color 0.2s ease`,
                borderLeft: "2px solid transparent",
              }}
              onMouseEnter={e => { const el = e.currentTarget; el.style.background = "#0d0d0d"; el.style.borderLeftColor = t.color; }}
              onMouseLeave={e => { const el = e.currentTarget; el.style.background = "#0a0a0a"; el.style.borderLeftColor = "transparent"; }}
            >
              <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: t.color, marginBottom: "14px", boxShadow: `0 0 8px ${t.color}66` }} />
              <p style={{ fontFamily: "var(--font-syne), sans-serif", fontWeight: 700, fontSize: "14px", color: "#e8e8e8", margin: "0 0 6px 0", letterSpacing: "-0.2px" }}>{t.name}</p>
              <p style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#333", margin: 0 }}>{t.role}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
