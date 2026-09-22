import React, { useState, useEffect } from 'react';
import {
  Button,
  Input,
  Select,
  Textarea,
  Checkbox,
  Callout,
  SourceMarker,
} from '../components/base';
import {
  api,
  type Claim,
  type Verdict,
  type LifecycleLedgerInput,
  type LifecycleLedger,
} from '../api/client';
import {
  VERDICT_LABELS,
  METRIC_LABELS,
  SOURCE_TYPE_LABELS,
} from '../api/labels';
import { ShieldCheck, Search, CheckCircle, AlertTriangle, XCircle, HelpCircle, RefreshCw } from 'lucide-react';
import styles from './ClaimAuditorPage.module.css';

export const ClaimAuditorPage: React.FC = () => {

  // Free-text extraction input
  const [rawText, setRawText] = useState(
    'Our distilled model achieves a 42% reduction in serving energy compared to the baseline with zero accuracy degradation.'
  );
  const [extracting, setExtracting] = useState(false);

  // Extracted/Edited Claim State
  const [claimText, setClaimText] = useState(
    '42% reduction in serving energy compared to baseline'
  );
  const [metric, setMetric] = useState<'energy' | 'carbon' | 'latency' | 'cost'>('energy');
  const [claimedPct, setClaimedPct] = useState('-42.0');
  const [baselineRef, setBaselineRef] = useState('BLOOM-176B');
  const [subjectRef, setSubjectRef] = useState('Distilled Compact Model');
  const [sourceType, setSourceType] = useState<'vendor' | 'paper' | 'model_card' | 'blog' | 'unknown'>('paper');
  const [extractionSource, setExtractionSource] = useState<'gemini' | 'rules_fallback' | 'user_specified'>('rules_fallback');

  // Boundary Stated
  const [includesTraining, setIncludesTraining] = useState(false);
  const [includesEmbodied, setIncludesEmbodied] = useState(false);
  const [accuracyReported, setAccuracyReported] = useState(true);
  const [accuracyPct, setAccuracyPct] = useState('0.0');

  // Audit Execution State
  const [checking, setChecking] = useState(false);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Extract Claim using API
  const handleExtract = async () => {
    if (!rawText.trim()) return;
    setExtracting(true);
    setError(null);
    try {
      const extracted = await api.extractClaim({ text: rawText });
      setClaimText(extracted.claim_text);
      setMetric(extracted.metric);
      setClaimedPct(extracted.claimed_change_pct?.toString() || '-42.0');
      setBaselineRef(extracted.baseline_ref || 'BLOOM-176B');
      setSubjectRef(extracted.subject_ref || 'Distilled Model');
      setSourceType(extracted.source_type);
      setExtractionSource(extracted.extraction_source);
      setIncludesTraining(!!extracted.boundary_stated.includes_training);
      setIncludesEmbodied(!!extracted.boundary_stated.includes_embodied);
      setAccuracyReported(extracted.accuracy_change_reported);
      setAccuracyPct(extracted.accuracy_change_pct?.toString() || '0.0');
    } catch (err: any) {
      setError(err.message || 'Failed to extract claim');
    } finally {
      setExtracting(false);
    }
  };

  // Run Multi-Tier Audit Cascade
  const handleCheck = async () => {
    setChecking(true);
    setError(null);
    try {
      // 1. Calculate realistic baseline and subject ledgers via backend /ledger
      const baseLedgerRes = await api.ledger({
        inventory: {
          model: { name: baselineRef, family: 'bloom', params_billions: 176, precision: 'fp16', framework: 'pytorch' },
          inference: { gpu: { model: 'NVIDIA A100 SXM4 80GB', count: 8, tdp_w: 400 }, runtime_hours: 8760, batch_size: 1, requests_per_day: 50000, avg_tokens_per_request: 512 },
          region: 'FRA',
          note: '',
        },
      });

      const subjLedgerRes = await api.ledger({
        inventory: {
          model: { name: subjectRef, family: 'bloom', params_billions: 70, precision: 'int8', framework: 'pytorch' },
          inference: { gpu: { model: 'NVIDIA A100 SXM4 80GB', count: 4, tdp_w: 400 }, runtime_hours: 8760, batch_size: 1, requests_per_day: 50000, avg_tokens_per_request: 512 },
          region: 'FRA',
          note: '',
        },
      });

      // Helper to strip readonly fields for LifecycleLedger-Input schema
      const toInput = (l: LifecycleLedger): LifecycleLedgerInput => ({
        boundary: l.boundary,
        training: l.training,
        inference: l.inference,
        embodied_hardware: l.embodied_hardware,
        retraining: l.retraining,
        storage: l.storage,
        network: l.network,
        energy_kwh: l.energy_kwh,
        per_request: l.per_request,
        assumptions: l.assumptions,
        schema_version: l.schema_version,
      });

      // 2. Call /claims/check with complete ClaimToLedgerMapping
      const claimPayload: Claim = {
        claim_text: claimText,
        metric: metric,
        claimed_change_pct: parseFloat(claimedPct) || -42.0,
        baseline_ref: baselineRef,
        subject_ref: subjectRef,
        boundary_stated: {
          includes_training: includesTraining,
          includes_embodied: includesEmbodied,
          accounting: 'location',
        },
        accuracy_change_reported: accuracyReported,
        accuracy_change_pct: parseFloat(accuracyPct) || 0.0,
        source_type: sourceType,
        extraction_source: extractionSource,
      };

      const verdictRes = await api.checkClaim({
        claim: claimPayload,
        baseline_ledger: toInput(baseLedgerRes.operational),
        subject_ledger: toInput(subjLedgerRes.operational),
        baseline_ledger_full: toInput(baseLedgerRes.full_lifecycle),
        subject_ledger_full: toInput(subjLedgerRes.full_lifecycle),
      });

      setVerdict(verdictRes);
    } catch (err: any) {
      setError(err.message || 'Audit verification check failed');
    } finally {
      setChecking(false);
    }
  };

  // Run initial check on mount
  useEffect(() => {
    if (!verdict && !checking) {
      handleCheck();
    }
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>AI Efficiency Claim Auditor & Cascade Verifier</h1>
        <p className={styles.pageSubtitle}>
          Audit efficiency and sustainability claims from papers or marketing copy against rigorous paired Monte Carlo uncertainty envelopes and boundary-shift detection rules.
        </p>
      </header>

      {error && (
        <Callout status="error" title="Audit Error">
          {error}
        </Callout>
      )}

      <div className={styles.layout}>
        {/* Left: Claim Extraction & Configuration */}
        <aside className={styles.claimPanel}>
          <h2 className={styles.panelTitle}>Claim Specification</h2>

          {/* Natural Language Extractor */}
          <Textarea
            label="Marketing Copy or Model Card Snippet"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            helperText="Paste free-form marketing, research claims, or press releases."
            rows={3}
          />

          <Button
            variant="secondary"
            size="sm"
            onClick={handleExtract}
            disabled={extracting}
            icon={extracting ? <RefreshCw className={styles.spinner} size={14} /> : <Search size={14} />}
          >
            {extracting ? 'Extracting Structure...' : 'Extract Claim Structure'}
          </Button>

          {/* Extraction Source Marker: Plain text with small square marker */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-2) 0' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', fontWeight: 600 }}>
              Extraction Provenance:
            </span>
            <SourceMarker source={extractionSource} />
          </div>

          <div className={styles.sectionDivider}>Structured Claim Parameters</div>

          <Input
            label="Extracted Claim Summary"
            value={claimText}
            onChange={(e) => setClaimText(e.target.value)}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <Select
              label="Audited Metric"
              value={metric}
              onChange={(e) => setMetric(e.target.value as any)}
              options={[
                { value: 'energy', label: METRIC_LABELS.energy },
                { value: 'carbon', label: METRIC_LABELS.carbon },
                { value: 'latency', label: METRIC_LABELS.latency },
                { value: 'cost', label: METRIC_LABELS.cost },
              ]}
            />
            <Input
              label="Claimed Relative Change"
              mono
              value={claimedPct}
              onChange={(e) => setClaimedPct(e.target.value)}
              suffix="%"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <Input
              label="Baseline System Ref"
              value={baselineRef}
              onChange={(e) => setBaselineRef(e.target.value)}
            />
            <Input
              label="Subject System Ref"
              value={subjectRef}
              onChange={(e) => setSubjectRef(e.target.value)}
            />
          </div>

          <Select
            label="Source Document Type"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value as any)}
            options={[
              { value: 'paper', label: SOURCE_TYPE_LABELS.paper },
              { value: 'model_card', label: SOURCE_TYPE_LABELS.model_card },
              { value: 'vendor', label: SOURCE_TYPE_LABELS.vendor },
              { value: 'blog', label: SOURCE_TYPE_LABELS.blog },
              { value: 'unknown', label: SOURCE_TYPE_LABELS.unknown },
            ]}
          />

          <div className={styles.sectionDivider}>Boundary Scope & Quality</div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <Checkbox
              label="Stated Scope Includes Training"
              checked={includesTraining}
              onChange={(e) => setIncludesTraining(e.target.checked)}
              description="Whether claim accounts for pre-training or fine-tuning emissions."
            />
            <Checkbox
              label="Stated Scope Includes Embodied Hardware"
              checked={includesEmbodied}
              onChange={(e) => setIncludesEmbodied(e.target.checked)}
              description="Whether claim includes manufacturing carbon."
            />
          </div>

          <Button
            variant="primary"
            size="lg"
            onClick={handleCheck}
            disabled={checking}
            icon={checking ? <RefreshCw className={styles.spinner} size={16} /> : <ShieldCheck size={16} />}
          >
            {checking ? 'Evaluating Cascade...' : 'Audit Claim Against Ledgers'}
          </Button>
        </aside>

        {/* Right: Cascade Verdict & Multi-Tier Reason Steps */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          {verdict && (
            <>
              {/* Verdict Banner */}
              <div className={`${styles.verdictBanner} ${styles[verdict.label]}`}>
                <div className={styles.verdictTitle}>
                  {verdict.label === 'supported' && <CheckCircle size={22} />}
                  {verdict.label === 'contradicted' && <XCircle size={22} />}
                  {verdict.label === 'suspicious_boundary_shift' && <AlertTriangle size={22} />}
                  {verdict.label === 'insufficient_evidence' && <HelpCircle size={22} />}
                  <span>{VERDICT_LABELS[verdict.label] || verdict.label}</span>
                </div>
                <div className={styles.verdictReason}>
                  Resolved by: <strong>{verdict.resolved_by}</strong> ({verdict.confidence != null ? `Confidence ${(verdict.confidence * 100).toFixed(0)}%` : 'Deterministic Cascade Check'})
                </div>

                {verdict.label === 'suspicious_boundary_shift' && (
                  <div style={{
                    marginTop: 'var(--space-2)',
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'rgba(0,0,0,0.06)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 600,
                  }}>
                    ⚠ Boundary Shift Detected: The claim evaluates operational efficiency gains while omitting lifecycle embodied carbon or training amortisation.
                  </div>
                )}
              </div>

              {/* Multi-Tier Cascade Reason Steps */}
              <div className={styles.stepsCard}>
                <div className={styles.stepsHeader}>
                  Deterministic Multi-Tier Verification Cascade
                </div>

                {verdict.reason_chain.map((s) => (
                  <div key={s.step} className={styles.stepItem}>
                    <div className={styles.stepTop}>
                      <span className={styles.stepCheck}>
                        Tier {s.step}: {s.check}
                      </span>
                      <span className={`${styles.stepResult} ${styles[s.result]}`}>
                        {s.result}
                      </span>
                    </div>
                    <div className={styles.stepEvidence}>
                      {s.evidence}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};
