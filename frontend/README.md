# BrandForge AI — Frontend

Next.js 14 App Router + TypeScript. See root [README.md](../README.md) for full project overview.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

## Pages

| Route | Purpose |
|---|---|
| `/` | Landing page with URL input |
| `/forge/[jobId]` | Live pipeline progress (SSE-driven) |
| `/forge/[jobId]/preview` | Generated brand kit preview + download |

## Key Files

- `lib/sse.ts` — Custom hook consuming the backend SSE stream
- `lib/api.ts` — Typed API client matching the backend contract exactly
- `components/forge/` — Pipeline visualization components
- `components/preview/` — Asset preview and download components

## Design System

Dark theme, amber (#f59e0b) accent only. Fonts: Syne (display), JetBrains Mono (labels/code). See `app/globals.css` for the full token system.
