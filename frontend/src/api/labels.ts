/**
 * Human-readable label maps for API enum values.
 * Internal identifiers must never be shown raw in the UI.
 */

export const BOUNDARY_LABELS: Record<string, string> = {
  operational: 'Operational Boundary',
  full_lifecycle: 'Full Lifecycle Boundary',
};

export const TIER_LABELS: Record<string, string> = {
  measured: 'Measured',
  modeled: 'Modelled',
};

export const PRECISION_LABELS: Record<string, string> = {
  fp32: 'FP32 (Full Precision)',
  fp16: 'FP16 (Half Precision)',
  bf16: 'BF16 (Brain Float)',
  int8: 'INT8 (8-bit Quantized)',
  int4: 'INT4 (4-bit Quantized)',
};

export const ACCOUNTING_LABELS: Record<string, string> = {
  location: 'Location-Based',
  market: 'Market-Based',
  unspecified: 'Unspecified',
};

export const ACCURACY_SOURCE_LABELS: Record<string, string> = {
  user_sample_eval: 'User Sample Evaluation',
  cited_published_delta: 'Cited Published Delta',
  not_available: 'Not Available',
};

export const VERDICT_LABELS: Record<string, string> = {
  supported: 'Claim Empirically Supported',
  contradicted: 'Claim Contradicted by Lifecycle Data',
  insufficient_evidence: 'Insufficient Lifecycle Evidence',
  suspicious_boundary_shift: 'Suspicious Boundary Shift Detected',
};

export const EXTRACTION_SOURCE_LABELS: Record<string, string> = {
  gemini: 'Gemini (LLM Extraction)',
  rules_fallback: 'Deterministic Rules Fallback',
  user_specified: 'User Specified Configuration',
};

export const METRIC_LABELS: Record<string, string> = {
  energy: 'Electricity Consumption (Energy)',
  carbon: 'Carbon Emissions (GHG)',
  latency: 'Latency (Response Time)',
  cost: 'Financial Cost',
};

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  vendor: 'Vendor Marketing Material',
  paper: 'Peer-Reviewed Research Paper',
  model_card: 'Official Model Card',
  blog: 'Engineering Blog Post',
  unknown: 'Unspecified Source Document',
};
