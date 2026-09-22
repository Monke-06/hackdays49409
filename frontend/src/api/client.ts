/**
 * Typed API client for the Sustainable AI Lifecycle Auditor backend.
 * All types are sourced from the generated types.ts (do not invent values).
 */
import type { components } from './types';

export type MetadataResponse = components['schemas']['MetadataResponse'];
export type LedgerRequest = components['schemas']['LedgerRequest'];
export type LedgerResponse = components['schemas']['LedgerResponse'];
export type LedgerEngineConfig = components['schemas']['LedgerEngineConfig'];
export type LifecycleLedger = components['schemas']['LifecycleLedger-Output'];
export type LifecycleLedgerInput = components['schemas']['LifecycleLedger-Input'];
export type LedgerAssumptions = components['schemas']['LedgerAssumptions'];
export type Quantity = components['schemas']['Quantity'];
export type SystemInventory = components['schemas']['SystemInventory'];
export type ModelSpec = components['schemas']['ModelSpec'];
export type GPUSpec = components['schemas']['GPUSpec'];
export type InferenceConfig = components['schemas']['InferenceConfig'];
export type TrainingConfig = components['schemas']['TrainingConfig'];
export type Boundary = components['schemas']['Boundary'];
export type HardwareOption = components['schemas']['HardwareOption'];
export type ModelPreset = components['schemas']['ModelPreset'];
export type RegionOption = components['schemas']['RegionOption'];
export type PresetScenario = components['schemas']['PresetScenario'];
export type HealthResponse = components['schemas']['HealthResponse'];
export type ParetoResult = components['schemas']['ParetoResult'];
export type RecommendRequest = components['schemas']['RecommendRequest'];
export type RecommenderCandidate = components['schemas']['RecommenderCandidate'];
export type ExtractClaimRequest = components['schemas']['ExtractClaimRequest'];
export type Claim = components['schemas']['Claim'];
export type ClaimToLedgerMapping = components['schemas']['ClaimToLedgerMapping'];
export type Verdict = components['schemas']['Verdict'];
export type VerdictLabel = components['schemas']['VerdictLabel'];
export type ReasonStep = components['schemas']['ReasonStep'];

// ─── Base fetcher ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} → ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ─── Endpoints ───────────────────────────────────────────────────────────────

export const api = {
  health(): Promise<HealthResponse> {
    return apiFetch('/api/v1/health');
  },

  meta(): Promise<MetadataResponse> {
    return apiFetch('/api/v1/meta');
  },

  ledger(request: LedgerRequest): Promise<LedgerResponse> {
    return apiFetch('/api/v1/ledger', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  recommend(request: RecommendRequest): Promise<ParetoResult> {
    return apiFetch('/api/v1/recommend', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  extractClaim(request: ExtractClaimRequest): Promise<Claim> {
    return apiFetch('/api/v1/claims/extract', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  checkClaim(mapping: ClaimToLedgerMapping): Promise<Verdict> {
    return apiFetch('/api/v1/claims/check', {
      method: 'POST',
      body: JSON.stringify(mapping),
    });
  },
};
