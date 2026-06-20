const API_BASE = "";

export async function startForge(url: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/forge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    let detail = `Server error (${res.status})`;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  const data = await res.json();
  if (!data.job_id) throw new Error("No job_id returned from server.");
  return data.job_id as string;
}

export interface ForgeResult {
  status: "complete" | "running" | "error";
  job_id: string;
  brand_name?: string;
  brand_tone?: string;
  brand_category?: string;
  target_audience?: string;
  brand_promise?: string;
  usps?: string[];
  tagline?: string;
  elevator_pitch?: string;
  brand_profile?: Record<string, unknown>;
  copy_output?: CopyOutput;
  email_output?: EmailOutput;
  ad_output?: AdOutput;
  layout_output?: LayoutOutput;
  zip_path?: string;
  scrape_status?: "success" | "partial" | "failed";
}

export interface CopyOutput {
  headlines?: { bold?: string[]; friendly?: string[]; professional?: string[] };
  hero_text?: { bold?: string; friendly?: string; professional?: string };
  subheadlines?: { bold?: string[]; friendly?: string[]; professional?: string[] };
  value_props?: { bold?: string[]; friendly?: string[]; professional?: string[] };
  call_to_actions?: { bold?: string[]; friendly?: string[]; professional?: string[] };
  tagline?: string;
  elevator_pitch?: string;
  usp_titles?: string[];
  usp_descriptions?: string[];
}

export interface EmailItem {
  subject?: string;
  preview_text?: string;
  headline?: string;
  body?: string;
  cta_text?: string;
  ps_line?: string;
}

export interface EmailOutput {
  email_welcome?: EmailItem;
  email_promo?: EmailItem;
  email_reengagement?: EmailItem;
  emails?: EmailItem[];
}

export interface AdOutput {
  headlines?: string[];
  body_copies?: string[];
  ctas?: string[];
  google_rsa?: { headlines?: string[]; descriptions?: string[] };
  meta_primary_text?: string;
  linkedin_ad?: { intro?: string; body?: string; cta?: string };
  hooks?: string[];
}

export interface LayoutOutput {
  template?: string;
  flyer_template?: string;
  content_density?: "low" | "medium" | "high";
  layout_emphasis?: string;
  color_application?: string;
  typography_mood?: string;
  social_card_layout?: string;
  email_header_style?: string;
  brand_category_tag?: string;
}

export async function getResult(jobId: string): Promise<ForgeResult> {
  const res = await fetch(`${API_BASE}/api/forge/${jobId}/result`);

  if (res.status === 202) {
    return { status: "running", job_id: jobId };
  }

  if (!res.ok) {
    let detail = `Failed to fetch result (${res.status})`;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return res.json() as Promise<ForgeResult>;
}

export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/forge/${jobId}/download`;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}