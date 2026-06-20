# BrandForge AI — UI Design Document

**Stack:** Next.js 14 · Tailwind CSS · shadcn/ui · Framer Motion  
**Design Direction:** Dark, editorial, precision-industrial — like a high-end creative studio tool

---

## 1. Design Philosophy

**Concept: "The Forge"**  
The UI should feel like an intelligent creative machine — dark, powerful, precise. Not a startup SaaS landing page. Think: a command center for brand creation. Dark backgrounds, sharp typography, accent colors that pulse with activity, motion that feels like mechanical precision.

**Aesthetic Direction:**
- **Theme:** Dark (near-black base) with a sharp amber/gold accent — the forge metaphor
- **Typography:** `Syne` (display/headings — geometric, distinctive) + `JetBrains Mono` (data/status) + `Inter` (body copy — the one exception since it's used sparingly)
- **Motion:** Purposeful and mechanical — progress bars that fill like molten metal, agents that "activate" with a subtle glow, results that slide in with staggered reveals
- **Color System:**
  ```
  --bg-base:      #0a0a0a   (near-black)
  --bg-surface:   #111111   (card surfaces)
  --bg-elevated:  #1a1a1a   (elevated elements)
  --border:       #2a2a2a   (subtle borders)
  --text-primary: #f0f0f0
  --text-muted:   #888888
  --accent:       #f59e0b   (amber — the "forge" color)
  --accent-dim:   #92400e
  --success:      #10b981
  --error:        #ef4444
  --agent-glow:   rgba(245, 158, 11, 0.15)
  ```

---

## 2. Pages Overview

| Route | Page | Description |
|---|---|---|
| `/` | Landing / Input | Hero section + URL input |
| `/forge/[jobId]` | Live Pipeline | Agent progress + results |
| `/forge/[jobId]/preview` | Asset Preview | Browse & download generated assets |

---

## 3. Page 1 — Landing / Input (`/`)

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  NAV: [BrandForge ⚡] ──────────────── [GitHub] [Docs]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│              HERO SECTION (full viewport)                │
│                                                          │
│    ┌──────────────────────────────────────────────┐     │
│    │  Superscript: "Multi-Agent Brand Intelligence" │     │
│    │                                               │     │
│    │  H1: "Turn any URL into                       │     │
│    │       a complete brand kit."                  │     │
│    │                                               │     │
│    │  Subtext: "7 AI agents. 60 seconds.           │     │
│    │  Flyers, emails, ads — all on-brand."         │     │
│    │                                               │     │
│    │  ┌─────────────────────────────────────────┐ │     │
│    │  │  https://your-company.com          [→]  │ │     │
│    │  └─────────────────────────────────────────┘ │     │
│    │                                               │     │
│    │  [  Forge Brand Kit  ]  ← amber CTA button   │     │
│    │                                               │     │
│    │  ─────────────────────────────────────────   │     │
│    │  Try: stripe.com · notion.so · linear.app    │     │
│    └──────────────────────────────────────────────┘     │
│                                                          │
│         [Animated background: subtle grid pattern]       │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                HOW IT WORKS (below fold)                 │
│                                                          │
│   ① Scrape    ② Understand    ③ Create    ④ Download    │
│   [icon]      [icon]          [icon]      [icon]         │
│   brief desc  brief desc      brief desc  brief desc     │
│                                                          │
├─────────────────────────────────────────────────────────┤
│              AGENT SHOWCASE (animated)                   │
│   "7 agents working in parallel for your brand"          │
│   [Copywriter] [Layout] [Email] [Ad] [Critic] ...        │
│    Each pulses on hover with amber glow                  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│              SAMPLE OUTPUT PREVIEW                       │
│   "What you'll receive" — static mockup cards           │
│   [Flyer Preview] [Social Card] [Email] [Ad Copy]        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Key Components

**`URLInput.tsx`**
- Large, full-width input with amber focus ring
- URL validation on blur (shows error if not valid URL)
- Loading state: input locks, spinner appears, redirects to `/forge/[jobId]`
- Keyboard: Enter key triggers submission
- Placeholder rotates through example URLs every 3 seconds

**Background Effect:**
- CSS grid pattern (very subtle, 1px lines at low opacity)
- Ambient gradient blob in amber, very low opacity, animated slow drift
- No JS-heavy canvas animations — pure CSS for performance

---

## 4. Page 2 — Live Pipeline (`/forge/[jobId]`)

This is the most important page. User watches agents work in real time.

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  NAV: [← Back] BrandForge          JOB ID: abc-1234     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │                     │  │                          │  │
│  │   AGENT TIMELINE    │  │   BRAND PROFILE          │  │
│  │   (left column)     │  │   (right column)         │  │
│  │                     │  │                          │  │
│  │  ● Scraping     ✓   │  │  [Appears after Stage 2] │  │
│  │  ● Extracting   ✓   │  │                          │  │
│  │  ● RAG Ingest   ✓   │  │  Brand: Acme Corp        │  │
│  │                     │  │  Tone: Bold & Confident  │  │
│  │  ┌─PARALLEL──────┐  │  │                          │  │
│  │  │ ◉ Copywriter  │  │  │  ████ ████ ████ ████    │  │
│  │  │ ◉ Layout      │  │  │  Color Palette           │  │
│  │  │ ◉ Email Agent │  │  │                          │  │
│  │  │ ◉ Ad Agent    │  │  │  Audience:               │  │
│  │  └───────────────┘  │  │  "B2B SaaS decision      │  │
│  │                     │  │   makers, 25-45"         │  │
│  │  ● Critic Agent ⟳   │  │                          │  │
│  │  ● Asset Gen    …   │  │  USPs:                   │  │
│  │  ● Packaging    …   │  │  • Fast setup            │  │
│  │                     │  │  • No-code solution      │  │
│  │  ─────────────────  │  │  • 10x cheaper           │  │
│  │  Overall: 67%  ████ │  │                          │  │
│  │                     │  │                          │  │
│  └─────────────────────┘  └──────────────────────────┘  │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  LIVE LOG (collapsible terminal-style feed)          │ │
│  │  > Scraping homepage... [200 OK]                    │ │
│  │  > Found 4 sub-pages. Scraping /about, /pricing...  │ │
│  │  > Extracted 6 brand colors from CSS               │ │
│  │  > Copywriter Agent: generating 5 headline options  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Agent Timeline States
Each agent node has 4 visual states:
- **Pending:** Dim circle, gray text, no activity
- **Running:** Amber pulsing dot, bright text, subtle glow background
- **Complete:** Green checkmark, muted text
- **Error:** Red X, error message inline

The parallel agents block shows all 4 running simultaneously with individual status indicators.

**`AgentTimeline.tsx`** — Core component  
Connects to SSE endpoint on mount. Each `data:` event from the stream updates the timeline state. Uses Framer Motion for state transitions.

```typescript
// SSE hook
function useAgentStream(jobId: string) {
  const [stages, setStages] = useState<StageMap>({})
  const [brandProfile, setBrandProfile] = useState(null)

  useEffect(() => {
    const es = new EventSource(`/api/forge/${jobId}/stream`)
    es.onmessage = (e) => {
      const event = JSON.parse(e.data)
      setStages(prev => ({ ...prev, [event.stage]: event }))
      if (event.stage === 'brand_extraction' && event.data) {
        setBrandProfile(event.data)
      }
    }
    return () => es.close()
  }, [jobId])

  return { stages, brandProfile }
}
```

**`BrandProfile.tsx`** — Slides in from right when brand extraction completes
- Color palette: circular swatches with hex values on hover
- Tone tag: amber badge
- USP list: staggered fade-in with Framer Motion
- Audience chip

**Live Log:**
- Monospace font (JetBrains Mono)
- Dark terminal background (#050505)
- New lines append at bottom, auto-scroll
- Collapsible (collapsed by default on mobile)
- Amber `>` prefix on each line

---

## 5. Page 3 — Asset Preview & Download (`/forge/[jobId]/preview`)

User lands here automatically when pipeline completes, or via "View Results" button.

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  NAV: [← New Brand] BrandForge AI   [↓ Download All]   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Brand: Acme Corp  •  Generated 2 min ago  •  ✓ 7 assets│
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Flyer] [Social Card] [Emails] [Ad Copy]  ← tab nav   │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                                                     │ │
│  │          ASSET PREVIEW (changes per tab)            │ │
│  │                                                     │ │
│  │  [PDF preview / PNG / HTML iframe / text preview]   │ │
│  │                                                     │ │
│  │  [  Download This Asset  ]  [  Regenerate  ]        │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌───────────────────────────────────────────────────┐   │
│  │  COPY VARIANTS (shown for ad copy / headlines)    │   │
│  │                                                   │   │
│  │  [Bold]  [Friendly]  [Professional]  ← toggles   │   │
│  │                                                   │   │
│  │  "10x your revenue — starting today"  [Copy ✓]   │   │
│  │  "Grow smarter, not harder"           [Copy ✓]   │   │
│  │  "Enterprise-grade tools, startup..." [Copy ✓]   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  ↓  DOWNLOAD BRAND KIT  (ZIP)                   │    │
│  │  6 files · ~2.4 MB  ·  brandforge_acme_corp.zip │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### `AssetPreview.tsx`
- Tab-based navigation for each asset type
- PDF preview: `<iframe>` with PDF URL
- PNG preview: `<img>` with zoom on click
- HTML email: `<iframe sandbox>` for safe render
- Ad copy: formatted text with one-click copy buttons per variant

### `DownloadKit.tsx`
- Big amber button — hard to miss
- Shows file count and estimated size
- Download triggers `/api/forge/{jobId}/download`
- Shows confetti animation on download (Framer Motion)

---

## 6. Component Map

```
src/components/
│
├── layout/
│   ├── Navbar.tsx          # Minimal dark nav
│   └── PageTransition.tsx  # Framer Motion page wrapper
│
├── home/
│   ├── Hero.tsx            # Headline + URL input
│   ├── HowItWorks.tsx      # 4-step explainer
│   ├── AgentShowcase.tsx   # Animated agent cards
│   └── SampleOutput.tsx    # Static preview mockups
│
├── forge/
│   ├── AgentTimeline.tsx   # SSE-powered progress feed
│   ├── AgentNode.tsx       # Individual agent status node
│   ├── ParallelBlock.tsx   # The fan-out parallel section
│   ├── BrandProfile.tsx    # Extracted brand data display
│   ├── ColorPalette.tsx    # Color swatch display
│   └── LiveLog.tsx         # Terminal-style event log
│
├── preview/
│   ├── AssetTabs.tsx       # Tab navigation
│   ├── AssetPreview.tsx    # Preview renderer (PDF/PNG/HTML)
│   ├── CopyVariants.tsx    # Toggle bold/friendly/pro
│   ├── CopyLine.tsx        # Single copy line + copy button
│   └── DownloadKit.tsx     # ZIP download CTA
│
└── ui/                     # shadcn components (auto-generated)
    ├── button.tsx
    ├── badge.tsx
    ├── tabs.tsx
    └── ...
```

---

## 7. Animation Spec

### Page Load (Landing)
```
0ms:    Navbar fades in
100ms:  Superscript slides up
200ms:  H1 slides up + fades in (word by word)
500ms:  Subtext fades in
700ms:  URL input slides up
900ms:  CTA button pulses in
1100ms: Sample URLs fade in
```

### Agent Running State
```css
/* Pulsing amber dot for running agents */
@keyframes agent-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  50%       { opacity: 0.7; box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
}
```

### Brand Profile Reveal
- Slides in from right with spring animation
- Color swatches stagger in one by one (50ms delay each)
- USPs fade in sequentially

### Pipeline Complete
- All nodes flash green in sequence
- "Complete" badge slides in on nav
- Page auto-navigates to `/preview` after 1.5s delay with smooth transition

---

## 8. Responsive Behavior

| Breakpoint | Changes |
|---|---|
| Desktop (>1024px) | Two-column layout on forge page |
| Tablet (768-1024px) | Stack columns, timeline on top |
| Mobile (<768px) | Single column, live log collapsed by default, larger touch targets |

---

## 9. Error States

| Scenario | UI Behavior |
|---|---|
| Invalid URL input | Red border + "Please enter a valid URL" inline |
| Scraping blocked | Yellow warning in timeline: "Site restricted — trying fallback..." |
| LLM rate limit | Info badge: "Switching to backup AI..." (transparent to user) |
| Full pipeline failure | Error card with "Try Again" button + error logged |
| Download fails | Toast notification: "Download failed. Try again." |
