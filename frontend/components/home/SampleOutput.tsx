"use client";
import { useEffect, useRef } from "react";

const ASSETS = [
  { label: "Brand Flyer", type: "PDF", desc: "Print-ready A4 flyer with brand colors, USPs, and CTA", preview: "flyer" },
  { label: "Social Card", type: "PNG 1080\u00d71080", desc: "Instagram/LinkedIn ready image with headline and brand palette", preview: "social" },
  { label: "Email Campaign", type: "3\u00d7 HTML", desc: "Welcome, promotional, and re-engagement email templates", preview: "email" },
  { label: "Ad Copy Kit", type: "PDF", desc: "Google RSA, Meta, LinkedIn, hooks, and headline variants", preview: "ads" },
  { label: "Brand Profile", type: "JSON", desc: "Structured brand intelligence for your CMS or other tools", preview: "json" },
  { label: "Brand Kit ZIP", type: "ZIP Bundle", desc: "All assets packaged and ready to download in one click", preview: "zip" },
];

function MockFlyer() {
  return (
    <div style={{ height: "140px", background: "#111", borderRadius: "6px", overflow: "hidden", display: "flex" }}>
      <div style={{ width: "40%", background: "#191919", padding: "12px 10px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div style={{ height: "4px", background: "#f59e0b", borderRadius: "2px", width: "60%" }} />
        <div>
          <div style={{ height: "8px", background: "#333", borderRadius: "2px", marginBottom: "4px" }} />
          <div style={{ height: "8px", background: "#333", borderRadius: "2px", width: "70%" }} />
        </div>
        <div style={{ height: "18px", background: "#f59e0b", borderRadius: "3px", width: "80%" }} />
      </div>
      <div style={{ flex: 1, padding: "12px 10px" }}>
        <div style={{ height: "6px", background: "#1a1a1a", borderRadius: "2px", marginBottom: "8px" }} />
        {[1,2,3].map(i => (
          <div key={i} style={{ display: "flex", gap: "6px", marginBottom: "6px" }}>
            <div style={{ width: "4px", height: "4px", borderRadius: "50%", background: "#f59e0b", marginTop: "2px", flexShrink: 0 }} />
            <div style={{ height: "4px", flex: 1, background: "#1a1a1a", borderRadius: "2px" }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function MockSocial() {
  return (
    <div style={{ height: "140px", background: "#191919", borderRadius: "6px", padding: "12px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div>
        <div style={{ height: "3px", background: "#f59e0b", borderRadius: "2px", width: "50%", marginBottom: "8px" }} />
        <div style={{ height: "20px", background: "#222", borderRadius: "2px", marginBottom: "4px" }} />
        <div style={{ height: "14px", background: "#1a1a1a", borderRadius: "2px", width: "70%" }} />
      </div>
      <div style={{ height: "24px", background: "#f59e0b", borderRadius: "12px", width: "55%", alignSelf: "center" }} />
    </div>
  );
}

function MockEmail() {
  return (
    <div style={{ height: "140px", background: "#111", borderRadius: "6px", overflow: "hidden" }}>
      <div style={{ background: "#191919", padding: "10px 12px" }}>
        <div style={{ height: "3px", background: "#f59e0b", borderRadius: "2px", width: "40%", marginBottom: "6px" }} />
        <div style={{ height: "14px", background: "#222", borderRadius: "2px" }} />
      </div>
      <div style={{ padding: "10px 12px" }}>
        {[1,2,3].map(i => (
          <div key={i} style={{ height: "4px", background: "#1a1a1a", borderRadius: "2px", marginBottom: "5px", width: `${100 - i*10}%` }} />
        ))}
        <div style={{ marginTop: "8px", height: "20px", background: "#f59e0b22", borderRadius: "3px", width: "45%", border: "1px solid #f59e0b44" }} />
      </div>
    </div>
  );
}

function MockAds() {
  return (
    <div style={{ height: "140px", background: "#111", borderRadius: "6px", padding: "12px" }}>
      <div style={{ marginBottom: "10px" }}>
        <div style={{ height: "4px", background: "#f59e0b", borderRadius: "2px", width: "30%", marginBottom: "6px" }} />
        {[1,2,3].map(i => (
          <div key={i} style={{ height: "4px", background: "#1a1a1a", borderRadius: "2px", marginBottom: "4px", width: `${70+i*8}%` }} />
        ))}
      </div>
      <div style={{ display: "flex", gap: "6px" }}>
        {["CTA 1","CTA 2","CTA 3"].map(c => (
          <div key={c} style={{ height: "20px", flex: 1, background: "#1a1a1a", borderRadius: "10px", border: "1px solid #f59e0b22" }} />
        ))}
      </div>
    </div>
  );
}

function MockJSON() {
  return (
    <div style={{ height: "140px", background: "#080808", borderRadius: "6px", padding: "10px 12px", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "9px", overflow: "hidden" }}>
      {[
        ['brand_name', '"Stripe"', '#10b981'],
        ['brand_tone', '"professional"', '#f59e0b'],
        ['colors.primary', '"#635bff"', '#8b5cf6'],
        ['usps', '[3 items]', '#3b82f6'],
        ['tagline', '"Built for..."', '#10b981'],
      ].map(([k, v, c]) => (
        <div key={k as string} style={{ marginBottom: "5px", display: "flex", gap: "6px" }}>
          <span style={{ color: "#333" }}>&quot;{k}&quot;:</span>
          <span style={{ color: c as string }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function MockZIP() {
  return (
    <div style={{ height: "140px", background: "#111", borderRadius: "6px", padding: "14px", display: "flex", flexDirection: "column", justifyContent: "center", gap: "8px" }}>
      {["flyer.pdf","social_card.png","email_welcome.html","ad_copy.pdf","brand_profile.json"].map(f => (
        <div key={f} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={{ width: "4px", height: "4px", borderRadius: "50%", background: "#f59e0b" }} />
          <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", color: "#333" }}>{f}</span>
        </div>
      ))}
    </div>
  );
}

const PREVIEWS: Record<string, React.ReactNode> = {
  flyer:  <MockFlyer />,
  social: <MockSocial />,
  email:  <MockEmail />,
  ads:    <MockAds />,
  json:   <MockJSON />,
  zip:    <MockZIP />,
};

export default function SampleOutput() {
  const cardsRef = useRef<(HTMLDivElement|null)[]>([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) {
          (e.target as HTMLElement).style.opacity = "1";
          (e.target as HTMLElement).style.transform = "translateY(0)";
        }
      }),
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    cardsRef.current.forEach(el => { if (el) observer.observe(el); });
    return () => observer.disconnect();
  }, []);

  return (
    <section style={{ padding: "96px 24px", backgroundColor: "#0a0a0a", borderTop: "1px solid #0e0e0e" }}>
      <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: "56px" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
            <span style={{ height: "1px", width: "32px", background: "linear-gradient(90deg, transparent, #f59e0b)", display: "block" }} />
            <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "10px", color: "#f59e0b", letterSpacing: "3px", textTransform: "uppercase" }}>What You Get</span>
            <span style={{ height: "1px", width: "32px", background: "linear-gradient(-90deg, transparent, #f59e0b)", display: "block" }} />
          </div>
          <h2 style={{ fontFamily: "var(--font-syne), sans-serif", fontWeight: 800, fontSize: "clamp(26px, 4vw, 40px)", color: "#f0f0f0", letterSpacing: "-1px", margin: 0 }}>
            Six assets. One URL. 90 seconds.
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
          {ASSETS.map((a, i) => (
            <div
              key={a.label}
              ref={el => { cardsRef.current[i] = el; }}
              className="forge-card"
              style={{ padding: "20px", opacity: 0, transform: "translateY(20px)", transition: `opacity 0.6s var(--forge-ease) ${i*0.08}s, transform 0.6s var(--forge-ease) ${i*0.08}s`, cursor: "default" }}
            >
              {PREVIEWS[a.preview]}
              <div style={{ marginTop: "16px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <p style={{ fontFamily: "var(--font-syne), sans-serif", fontWeight: 700, fontSize: "15px", color: "#e8e8e8", margin: "0 0 4px 0" }}>{a.label}</p>
                  <p style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "11px", color: "#444", margin: 0, lineHeight: 1.5 }}>{a.desc}</p>
                </div>
                <span className="forge-badge" style={{ flexShrink: 0, marginLeft: "12px", marginTop: "2px" }}>{a.type}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
