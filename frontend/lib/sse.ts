"use client";
import { useState, useEffect, useRef, useCallback } from "react";

export type AgentStatus =
  | "pending"
  | "running"
  | "progress"
  | "done"
  | "complete"
  | "warning"
  | "failed"
  | "success"
  | "started";

export interface AgentEvent {
  type?: string;
  stage?: string;
  status: AgentStatus;
  message?: string;
  data?: unknown;
  progress?: number;
  download_url?: string;
  brand_name?: string;
  error?: string;
}

export interface BrandProfileData {
  brand_name?: string;
  brand_category?: string;
  brand_tone?: string;
  target_audience?: string;
  brand_promise?: string;
  usps?: string[];
  key_products_services?: string[];
  competitive_edge?: string;
  emotional_benefit?: string;
  brand_archetype?: string;
  visual_style?: string;
  pricing_model?: string;
  content_themes?: string[];
  brand_voice_examples?: string[];
  colors?: {
    primary?: string;
    secondary?: string;
    accent?: string;
    background?: string;
    text?: string;
  };
}

export interface UseAgentStreamResult {
  stages: Record<string, AgentEvent>;
  brandProfile: BrandProfileData | null;
  isComplete: boolean;
  downloadUrl: string | null;
  error: string | null;
  logs: string[];
  progress: number;
}

const STALE_TIMEOUT_MS = 90_000;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 3_000;

const PIPELINE_STAGES = [
  "scraper",
  "brand_extractor",
  "rag_ingestor",
  "copywriter",
  "layout_agent",
  "email_agent",
  "ad_agent",
  "critic",
  "asset_generator",
  "zip_packager",
];

function computeProgress(stages: Record<string, AgentEvent>): number {
  if (!Object.keys(stages).length) return 0;
  const doneCount = PIPELINE_STAGES.filter((s) => {
    const ev = stages[s];
    return ev && (ev.status === "done" || ev.status === "complete" || ev.status === "success");
  }).length;
  return Math.round((doneCount / PIPELINE_STAGES.length) * 100);
}

function makeLogLine(event: AgentEvent): string {
  const now = new Date().toTimeString().slice(0, 8);
  const stage = event.type || event.stage || "pipeline";
  let line = `[${now}] [${stage.toUpperCase()}] ${event.status.toUpperCase()}`;
  if (event.message) line += ` — ${event.message}`;
  if (event.error) line += ` ⚠ ${event.error}`;
  return line;
}

export function useAgentStream(jobId: string): UseAgentStreamResult {
  const [stages, setStages] = useState<Record<string, AgentEvent>>({});
  const [brandProfile, setBrandProfile] = useState<BrandProfileData | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);

  const esRef = useRef<EventSource | null>(null);
  const staleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const isCompleteRef = useRef(false);
  const stagesRef = useRef<Record<string, AgentEvent>>({});

  const appendLog = useCallback((line: string) => {
    setLogs((prev) => [...prev.slice(-199), line]);
  }, []);

  const clearStaleTimer = useCallback(() => {
    if (staleTimerRef.current) {
      clearTimeout(staleTimerRef.current);
      staleTimerRef.current = null;
    }
  }, []);

  const resetStaleTimer = useCallback(() => {
    clearStaleTimer();
    staleTimerRef.current = setTimeout(() => {
      if (!isCompleteRef.current) {
        const msg = "Pipeline stalled — no activity for 90 seconds.";
        setError(msg);
        appendLog(`[SYSTEM] ⚠ ${msg}`);
        esRef.current?.close();
      }
    }, STALE_TIMEOUT_MS);
  }, [clearStaleTimer, appendLog]);

  useEffect(() => {
    if (!jobId) return;
    isCompleteRef.current = false;
    stagesRef.current = {};

    const connect = () => {
      if (isCompleteRef.current) return;

      esRef.current?.close();
      const es = new EventSource(`/api/forge/${jobId}/stream`);
      esRef.current = es;
      resetStaleTimer();

      es.onmessage = (raw) => {
        // Heartbeat ping — reset stale timer but don't process
        if (raw.data === "" || raw.data === ": ping" || raw.data?.startsWith(":")) {
          resetStaleTimer();
          return;
        }

        let event: AgentEvent;
        try {
          event = JSON.parse(raw.data) as AgentEvent;
        } catch {
          return;
        }

        resetStaleTimer();
        retryCountRef.current = 0;

        const stageKey = event.type || event.stage || "pipeline";

        // Update stages
        const updated = { ...stagesRef.current, [stageKey]: event };
        stagesRef.current = updated;
        setStages({ ...updated });
        setProgress(computeProgress(updated));

        // Append to terminal log
        appendLog(makeLogLine(event));

        // Extract brand profile from brand_extractor event
        if (stageKey === "brand_extractor" && event.data) {
          setBrandProfile(event.data as BrandProfileData);
        }

        // Handle terminal states
        const isTerminalComplete =
          event.type === "complete" ||
          event.stage === "complete" ||
          event.status === "complete" ||
          event.status === "success";

        const isTerminalError =
          event.type === "error" ||
          event.stage === "error" ||
          event.status === "failed";

        if (isTerminalComplete) {
          isCompleteRef.current = true;
          setIsComplete(true);
          setProgress(100);
          if (event.download_url) setDownloadUrl(event.download_url);
          appendLog(`[SYSTEM] ✓ Pipeline complete. Brand kit ready.`);
          es.close();
          clearStaleTimer();
        } else if (isTerminalError) {
          const errMsg = event.message || event.error || "Pipeline failed unexpectedly.";
          setError(errMsg);
          appendLog(`[SYSTEM] ✗ Error: ${errMsg}`);
          es.close();
          clearStaleTimer();
        }
      };

      es.onerror = () => {
        es.close();
        if (isCompleteRef.current) return;

        if (retryCountRef.current < MAX_RETRIES) {
          retryCountRef.current += 1;
          const attempt = retryCountRef.current;
          appendLog(
            `[SYSTEM] Connection lost. Reconnecting in ${RETRY_DELAY_MS / 1000}s... (${attempt}/${MAX_RETRIES})`
          );
          reconnectTimerRef.current = setTimeout(connect, RETRY_DELAY_MS);
        } else {
          const msg = `Connection failed after ${MAX_RETRIES} retries.`;
          setError(msg);
          appendLog(`[SYSTEM] ✗ ${msg}`);
          clearStaleTimer();
        }
      };
    };

    connect();

    return () => {
      isCompleteRef.current = true;
      esRef.current?.close();
      clearStaleTimer();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, [jobId, resetStaleTimer, clearStaleTimer, appendLog]);

  return { stages, brandProfile, isComplete, downloadUrl, error, logs, progress };
}