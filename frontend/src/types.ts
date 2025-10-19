export type HSRuleHit = { code: string; confidence: number; rationale: string[]; required_uom: string };
export type HSResponse = {
  hs_candidates: HSRuleHit[];
  duty_rate: { ad_valorem_pct: number; additional: string[] };
  risk_flags: { ad_cvd: boolean; import_alert: boolean };
  quota_applicability: string;
  review_required: boolean;
};
export type Job = {
  type: 'pack'|'pn';
  status: 'queued'|'running'|'submitted'|'completed'|'accepted'|'rejected'|'error';
  trace_id: string;
  artifacts?: { media_id: string; sha256: string; size: number; type: string }[];
  error?: unknown;
};
