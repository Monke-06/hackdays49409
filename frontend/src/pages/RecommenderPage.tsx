import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Button,
  Input,
  Select,
  Callout,
  QuantityDisplay,
  Table,
} from '../components/base';
import {
  api,
  type MetadataResponse,
  type ParetoResult,
  type SystemInventory,
  type RecommenderCandidate,
} from '../api/client';
import { BOUNDARY_LABELS, PRECISION_LABELS } from '../api/labels';
import { Sparkles, Sliders, RefreshCw } from 'lucide-react';
import styles from './RecommenderPage.module.css';

export const RecommenderPage: React.FC = () => {
  const [meta, setMeta] = useState<MetadataResponse | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);

  // Form Inputs
  const [modelName, setModelName] = useState('LLaMA-3-8B');
  const modelFamily = 'llama';
  const [paramsBillions, setParamsBillions] = useState('8.0');
  const [precision, setPrecision] = useState<'fp32' | 'fp16' | 'bf16' | 'int8' | 'int4'>('fp16');
  const [gpuModel, setGpuModel] = useState('NVIDIA A100 SXM4 80GB');
  const [gpuCount, setGpuCount] = useState('4');
  const [latencyLimitMs, setLatencyLimitMs] = useState('250.0');
  const [region, setRegion] = useState('FRA');
  const [boundary, setBoundary] = useState<'operational' | 'full_lifecycle'>('full_lifecycle');

  // Traffic volume slider state for break-even exploration
  const [simulatedTraffic, setSimulatedTraffic] = useState<number>(100000);

  // Recommender Results
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ParetoResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch metadata on mount
  useEffect(() => {
    let mounted = true;
    api.meta()
      .then((data) => {
        if (!mounted) return;
        setMeta(data);
        setMetaLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message);
        setMetaLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const buildInventory = useCallback((): SystemInventory => {
    return {
      model: {
        name: modelName,
        family: modelFamily,
        params_billions: parseFloat(paramsBillions) || 8.0,
        precision: precision,
        framework: 'pytorch',
      },
      inference: {
        gpu: {
          model: gpuModel,
          count: parseInt(gpuCount, 10) || 1,
          tdp_w: 400.0,
        },
        runtime_hours: 8760.0,
        batch_size: 1,
        requests_per_day: simulatedTraffic,
        avg_tokens_per_request: 512,
        p95_latency_limit_ms: latencyLimitMs ? parseFloat(latencyLimitMs) : null,
      },
      region: region,
      note: '',
    };
  }, [
    modelName, modelFamily, paramsBillions, precision, gpuModel, gpuCount,
    simulatedTraffic, latencyLimitMs, region
  ]);

  const runRecommender = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inv = buildInventory();
      const res = await api.recommend({
        inventory: inv,
        boundary: boundary,
      });
      setResult(res);
      if (res.break_even_full_lifecycle_requests) {
        // initialize break-even slider to reasonable midpoint if available
      }
    } catch (err: any) {
      setError(err.message || 'Failed to compute architecture recommendations');
    } finally {
      setLoading(false);
    }
  }, [buildInventory, boundary]);

  useEffect(() => {
    if (meta && !result && !loading) {
      runRecommender();
    }
  }, [meta, result, loading, runRecommender]);

  // SVG Scatter plot bounds
  const scatterPoints = useMemo(() => {
    if (!result || !result.candidates) return [];
    return result.candidates.map((c) => {
      const opCarbon = c.ledger_operational.total_carbon.value;
      const fullCarbon = c.ledger_full.total_carbon.value;
      const latency = c.p95_latency_ms ? c.p95_latency_ms.value : 50;
      const isParetoOp = (result.pareto_points_operational || []).includes(c.label);
      const isParetoFull = (result.pareto_points_full_lifecycle || []).includes(c.label);
      const isWinnerOp = result.winner_operational === c.label;
      const isWinnerFull = result.winner_full_lifecycle === c.label;

      return {
        candidate: c,
        label: c.label,
        opCarbon,
        fullCarbon,
        latency,
        isParetoOp,
        isParetoFull,
        isWinnerOp,
        isWinnerFull,
        qualifies: c.latency_constraint_met,
      };
    });
  }, [result]);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>AI Architecture Recommender & Pareto Frontier</h1>
        <p className={styles.pageSubtitle}>
          Evaluate architectural alternatives (quantization, distillation, model routing) across both operational and full-lifecycle boundaries to find the Pareto optimal configurations without greenwashing.
        </p>
      </header>

      {error && (
        <Callout status="error" title="Recommender Error">
          {error}
        </Callout>
      )}

      <div className={styles.layout}>
        {/* Left: Input Constraints */}
        <aside className={styles.inputsPanel}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 className={styles.inputsPanelTitle}>Workload Constraints</h2>
            <Sliders size={16} color="var(--color-text-muted)" />
          </div>

          <div className={styles.sectionDivider}>Baseline Model</div>
          <Input
            label="Baseline Model"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <Input
              label="Parameters"
              mono
              value={paramsBillions}
              onChange={(e) => setParamsBillions(e.target.value)}
              suffix="B"
            />
            <Select
              label="Precision"
              value={precision}
              onChange={(e) => setPrecision(e.target.value as any)}
              options={[
                { value: 'fp32', label: PRECISION_LABELS.fp32 },
                { value: 'fp16', label: PRECISION_LABELS.fp16 },
                { value: 'bf16', label: PRECISION_LABELS.bf16 },
                { value: 'int8', label: PRECISION_LABELS.int8 },
                { value: 'int4', label: PRECISION_LABELS.int4 },
              ]}
            />
          </div>

          <div className={styles.sectionDivider}>Performance & Hardware</div>
          {meta && (
            <Select
              label="Accelerator"
              value={gpuModel}
              onChange={(e) => setGpuModel(e.target.value)}
              options={meta.hardware.map((h) => ({
                value: h.model,
                label: `${h.model} (${h.tdp_w}W)`,
              }))}
            />
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <Input
              label="Device Count"
              mono
              value={gpuCount}
              onChange={(e) => setGpuCount(e.target.value)}
              suffix="Units"
            />
            <Input
              label="Max P95 Latency"
              mono
              value={latencyLimitMs}
              onChange={(e) => setLatencyLimitMs(e.target.value)}
              suffix="ms"
              helperText="Hard SLA cutoff"
            />
          </div>

          <div className={styles.sectionDivider}>Region & Optimization Goal</div>
          {meta && (
            <Select
              label="Region"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              options={meta.regions.map((r) => ({
                value: r.code,
                label: `${r.name} (${r.intensity_gco2_per_kwh.toFixed(0)} g/kWh)`,
              }))}
            />
          )}

          <Select
            label="Optimization Boundary"
            value={boundary}
            onChange={(e) => setBoundary(e.target.value as any)}
            options={[
              { value: 'operational', label: BOUNDARY_LABELS.operational },
              { value: 'full_lifecycle', label: BOUNDARY_LABELS.full_lifecycle },
            ]}
          />

          <Button
            variant="primary"
            size="lg"
            onClick={runRecommender}
            disabled={loading || metaLoading}
            icon={loading ? <RefreshCw className={styles.spinner} size={16} /> : <Sparkles size={16} />}
          >
            {loading ? 'Evaluating Frontier...' : 'Explore Pareto Frontier'}
          </Button>
        </aside>

        {/* Right: Recommendations, Frontier Chart, Break-even Slider */}
        <section className={styles.resultsPanel}>
          {/* 1. Binding Constraint Handling: When nothing qualifies, NEVER show a recommendation */}
          {result && (result.qualifying_candidates_count === 0 || (!result.winner_operational && !result.winner_full_lifecycle)) ? (
            <Callout status="error" title="No Qualifying Architectures Found">
              <p>
                <strong>Binding Constraint:</strong> {result.binding_constraint || 'All candidate configurations violated the hard performance or latency constraints.'}
              </p>
              <p style={{ marginTop: 'var(--space-2)' }}>
                No recommendation can be made under these constraints. Try increasing the P95 latency limit or reducing model parameter scale.
              </p>
            </Callout>
          ) : result && (
            <>
              {/* Winner Changed Warning Banner */}
              {result.winner_changed && (
                <Callout status="warning" title="Boundary Reversal Detected">
                  The recommended optimal architecture changes when accounting for amortized embodied hardware manufacturing carbon versus operational energy alone. Inspect the dual boundary cards below.
                </Callout>
              )}

              {/* Dual-Boundary Winner Cards */}
              <div className={styles.winnerGrid}>
                <div className={styles.winnerCard}>
                  <span className={styles.winnerBoundaryLabel}>
                    Operational Winner (Energy Only)
                  </span>
                  <div className={styles.winnerTitle}>
                    {result.winner_operational || 'None Qualified'}
                  </div>
                  <div className={styles.winnerScore}>
                    Ranked #1 for runtime operational carbon efficiency.
                  </div>
                </div>

                <div className={styles.winnerCard} style={{ borderColor: 'var(--color-action-primary)' }}>
                  <span className={styles.winnerBoundaryLabel} style={{ color: 'var(--color-action-primary)' }}>
                    Full Lifecycle Winner (Cradle-to-Grave)
                  </span>
                  <div className={styles.winnerTitle}>
                    {result.winner_full_lifecycle || 'None Qualified'}
                  </div>
                  <div className={styles.winnerScore}>
                    Ranked #1 when amortising embodied manufacturing emissions.
                  </div>
                </div>
              </div>

              {/* Interactive Break-even Traffic Slider */}
              <div className={styles.sliderCard}>
                <div className={styles.chartHeader}>
                  <h3 className={styles.sliderTitle}>Life-Cycle Break-Even Sensitivity Explorer</h3>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {simulatedTraffic.toLocaleString('en-GB')} req/day
                  </span>
                </div>

                <div className={styles.sliderRow}>
                  <input
                    type="range"
                    min="1000"
                    max="1000000"
                    step="5000"
                    value={simulatedTraffic}
                    onChange={(e) => setSimulatedTraffic(parseInt(e.target.value, 10))}
                    className={styles.sliderInput}
                    aria-label="Simulated Daily Request Volume"
                  />
                  <div className={styles.sliderLabels}>
                    <span>1k req/day (Edge/Infrequent)</span>
                    <span>100k req/day (Production)</span>
                    <span>1M req/day (Hyperscale)</span>
                  </div>
                </div>

                {result.break_even_full_lifecycle_requests ? (
                  <div className={styles.breakEvenCallout}>
                    <strong>Break-even crossover:</strong> Amortised embodied manufacturing costs equal operational savings at approximately{' '}
                    <strong>{result.break_even_full_lifecycle_requests.toLocaleString('en-GB')} total lifetime requests</strong>.
                    Below this threshold, deploying smaller or specialized hardware yields higher total emissions than keeping general-purpose infrastructure.
                  </div>
                ) : (
                  <div className={styles.breakEvenCallout}>
                    Selected candidates share identical hardware footprints; comparative emissions scale proportionally without hardware amortisation crossovers.
                  </div>
                )}
              </div>

              {/* SVG Scatter Plot / Pareto Frontier */}
              <div className={styles.chartContainer}>
                <div className={styles.chartHeader}>
                  <h3 className={styles.chartTitle}>
                    Multi-Objective Pareto Frontier ({BOUNDARY_LABELS[boundary]})
                  </h3>
                  <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
                    Operational Carbon (kgCO₂e) vs P95 Latency (ms)
                  </span>
                </div>

                <svg className={styles.svgChart} viewBox="0 0 600 300" role="img" aria-label="Pareto Frontier Scatter Plot">
                  {/* Grid Lines */}
                  <line x1="60" y1="20" x2="60" y2="250" stroke="var(--color-border-subtle)" strokeWidth="1" />
                  <line x1="60" y1="250" x2="560" y2="250" stroke="var(--color-border-subtle)" strokeWidth="1" />

                  {/* Axis Labels */}
                  <text x="310" y="280" textAnchor="middle" fill="var(--color-text-secondary)" fontSize="11" fontFamily="var(--font-sans)">
                    Total Carbon Footprint (kg CO₂e) →
                  </text>
                  <text x="20" y="140" textAnchor="middle" fill="var(--color-text-secondary)" fontSize="11" fontFamily="var(--font-sans)" transform="rotate(-90 20 140)">
                    P95 Latency (ms) →
                  </text>

                  {/* Render Candidates */}
                  {scatterPoints.map((pt) => {
                    // Normalize X and Y inside viewbox (60 to 540 X, 30 to 240 Y)
                    const minCarbon = Math.min(...scatterPoints.map((p) => p.fullCarbon), 1);
                    const maxCarbon = Math.max(...scatterPoints.map((p) => p.fullCarbon), 10);
                    const minLat = Math.min(...scatterPoints.map((p) => p.latency), 1);
                    const maxLat = Math.max(...scatterPoints.map((p) => p.latency), 100);

                    const cx = 80 + ((pt.fullCarbon - minCarbon) / Math.max(maxCarbon - minCarbon, 1)) * 440;
                    const cy = 230 - ((pt.latency - minLat) / Math.max(maxLat - minLat, 1)) * 180;

                    const isWinner = boundary === 'operational' ? pt.isWinnerOp : pt.isWinnerFull;
                    const isPareto = boundary === 'operational' ? pt.isParetoOp : pt.isParetoFull;

                    return (
                      <g key={pt.label}>
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isWinner ? 7 : (isPareto ? 5.5 : 4)}
                          fill={
                            !pt.qualifies
                              ? 'var(--color-status-error-border)'
                              : isWinner
                              ? 'var(--color-action-primary)'
                              : isPareto
                              ? 'var(--color-status-success-text)'
                              : 'var(--color-border-strong)'
                          }
                          stroke={isWinner ? 'var(--color-bg-surface)' : 'none'}
                          strokeWidth={isWinner ? 2 : 0}
                          className={styles.plotPoint}
                        >
                          <title>{`${pt.label}: ${pt.fullCarbon.toFixed(1)} kgCO2e, ${pt.latency.toFixed(1)} ms`}</title>
                        </circle>
                        <text
                          x={cx + 8}
                          y={cy + 4}
                          fontSize="10"
                          fontFamily="var(--font-mono)"
                          fill={isWinner ? 'var(--color-text-primary)' : 'var(--color-text-muted)'}
                          fontWeight={isWinner ? 'bold' : 'normal'}
                        >
                          {pt.label} {isWinner ? '★' : ''}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-sans)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ width: 8, height: 8, backgroundColor: 'var(--color-action-primary)', display: 'inline-block' }} />
                    Recommended Winner
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ width: 8, height: 8, backgroundColor: 'var(--color-status-success-text)', display: 'inline-block' }} />
                    Pareto Optimal Front
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ width: 8, height: 8, backgroundColor: 'var(--color-border-strong)', display: 'inline-block' }} />
                    Dominated Candidate
                  </span>
                </div>
              </div>

              {/* Dual Boundary Candidate Rankings Table */}
              <div className={styles.rankingsCard}>
                <div className={styles.rankingsHeader}>
                  <h3 className={styles.chartTitle}>Candidate Architecture Comparative Audit</h3>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    {result.candidates.length} evaluated
                  </span>
                </div>

                <Table<RecommenderCandidate>
                  columns={[
                    { header: 'Architecture Candidate', accessor: 'label' },
                    {
                      header: 'Operational Carbon',
                      accessor: (row: RecommenderCandidate) => (
                        <QuantityDisplay quantity={row.ledger_operational.total_carbon} compact />
                      ),
                    },
                    {
                      header: 'Full Lifecycle Carbon',
                      accessor: (row: RecommenderCandidate) => (
                        <QuantityDisplay quantity={row.ledger_full.total_carbon} compact />
                      ),
                    },
                    {
                      header: 'P95 Latency',
                      accessor: (row: RecommenderCandidate) => (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
                          {row.p95_latency_ms ? `${row.p95_latency_ms.value.toFixed(1)} ms` : 'N/A'}
                        </span>
                      ),
                    },
                    {
                      header: 'Constraint Status',
                      accessor: (row: RecommenderCandidate) => (
                        <span style={{
                          fontFamily: 'var(--font-sans)',
                          fontSize: 'var(--font-size-xs)',
                          fontWeight: 600,
                          color: row.latency_constraint_met ? 'var(--color-status-success-text)' : 'var(--color-status-error-text)',
                        }}>
                          {row.latency_constraint_met ? 'Qualified' : `Violates SLA: ${row.latency_exclusion_reason || 'P95 Exceeded'}`}
                        </span>
                      ),
                    },
                  ]}
                  data={result.candidates}
                  keyExtractor={(c) => c.label}
                />
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};
