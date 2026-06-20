import Hero from "@/components/home/Hero";
import HowItWorks from "@/components/home/HowItWorks";
import TechStack from "@/components/home/TechStack";
import SampleOutput from "@/components/home/SampleOutput";

export default function HomePage() {
  return (
    <main style={{ background: "#0a0a0a", minHeight: "100vh" }}>
      <Hero />
      <HowItWorks />
      <TechStack />
      <SampleOutput />
      <footer style={{
        borderTop: "1px solid #111",
        padding: "32px 24px",
        textAlign: "center",
        fontFamily: "var(--font-jetbrains-mono), monospace",
        fontSize: "11px",
        color: "#2a2a2a",
        letterSpacing: "1px",
      }}>
        BRANDFORGE AI — MULTI-AGENT BRAND INTELLIGENCE
        &nbsp;&nbsp;·&nbsp;&nbsp;
        BUILT WITH LANGGRAPH · CHROMADB · GROQ · NEXT.JS
      </footer>
    </main>
  );
}
