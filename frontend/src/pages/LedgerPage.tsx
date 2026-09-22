import React, { useState, useEffect, useCallback } from 'react';
import {
  Button,
  Input,
  Select,
  Callout,
  QuantityDisplay,
} from '../components/base';
import { AssumptionsDrawer } from '../components/ledger/AssumptionsDrawer';
import { api, type MetadataResponse, type LedgerResponse, type SystemInventory } from '../api/client';
import { BOUNDARY_LABELS, PRECISION_LABELS } from '../api/labels';
import { RefreshCw, HelpCircle, Layers, Sliders, Download } from 'lucide-react';
import { exportLedgerToJSON, exportLedgerToCSV } from '../utils/export';
import styles from './LedgerPage.module.css';

export const LedgerPage: React.FC = () => {
  // Metadata state
  const [meta, setMeta] = useState<MetadataResponse | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);

  // Active form inputs (SystemInventory)
  const [selectedPresetId, setSelectedPresetId] = useState<string>('bloom_training');
  const [modelName, setModelName] = useState<string>('BLOOM-176B');
  const [modelFamily, setModelFamily] = useState<string>('bloom');
  const [paramsBillions, setParamsBillions] = useState<string>('176.0');
  const [precision, setPrecision] = useState<'fp32' | 'fp16' | 'bf16' | 'int8' | 'int4'>('fp16');

  const [gpuModel, setGpuModel] = useState<string>('NVIDIA A100 SXM4 80GB');
  const [gpuCount, setGpuCount] = useState<string>('384');
  const [gpuTdp, setGpuTdp] = useState<string>('400.0');

  const [mode, setMode] = useState<'training' | 'inference'>('training');
  const [durationHours, setDurationHours] = useState<string>('2832.0');
  const [pue, setPue] = useState<string>('1.2');
  const [requestsPerDay, setRequestsPerDay] = useState<string>('50000');
  const [tokensPerRequest, setTokensPerRequest] = useState<string>('512');
  const [region, setRegion] = useState<string>('FRA');

  // Ledger computation state
  const [ledgerData, setLedgerData] = useState<LedgerResponse | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  // Active boundary display toggle
  const [boundary, setBoundary] = useState<'operational' | 'full_lifecycle'>('full_lifecycle');

  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Fetch metadata on mount
  useEffect(() => {
    let isMounted = true;
    api.meta()
      .then((data) => {
        if (!isMounted) return;
        setMeta(data);
        setMetaLoading(false);
        // If preset scenarios exist, apply initial preset
        if (data.preset_scenarios && data.preset_scenarios.length > 0) {
          applyPreset(data.preset_scenarios[0]);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setMetaError(err.message || 'Failed to load metadata from backend');
        setMetaLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const applyPreset = (preset: MetadataResponse['preset_scenarios'][0]) => {
    setSelectedPresetId(preset.id);
    const inv = preset.inventory;
    if (inv.model) {
      setModelName(inv.model.name);
      setModelFamily(inv.model.family);
      setParamsBillions(inv.model.params_billions.toString());
      setPrecision(inv.model.precision as any);
    }
    if (inv.region) {
      setRegion(inv.region);
    }
    if (inv.training) {
      setMode('training');
      setGpuModel(inv.training.gpu.model);
      setGpuCount(inv.training.gpu.count.toString());
      setGpuTdp(inv.training.gpu.tdp_w?.toString() || '400.0');
      setDurationHours(inv.training.duration_hours.toString());
      if (inv.training.pue) setPue(inv.training.pue.toString());
    } else if (inv.inference) {
      setMode('inference');
      setGpuModel(inv.inference.gpu.model);
      setGpuCount(inv.inference.gpu.count.toString());
      setGpuTdp(inv.inference.gpu.tdp_w?.toString() || '400.0');
      setRequestsPerDay(inv.inference.requests_per_day.toString());
      setTokensPerRequest(inv.inference.avg_tokens_per_request.toString());
    }
  };

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId);
    if (!meta) return;
    const found = meta.preset_scenarios.find((p) => p.id === presetId);
    if (found) applyPreset(found);
  };

  const buildInventory = useCallback((): SystemInventory => {
    const inv: SystemInventory = {
      model: {
        name: modelName,
        family: modelFamily,
        params_billions: parseFloat(paramsBillions) || 1.0,
        precision: precision,
        framework: 'pytorch',
      },
      region: region,
      note: '',
    };

    const gpuSpec = {
      model: gpuModel,
      count: parseInt(gpuCount, 10) || 1,
      tdp_w: parseFloat(gpuTdp) || 300.0,
    };

    if (mode === 'training') {
      inv.training = {
        gpu: gpuSpec,
        duration_hours: parseFloat(durationHours) || 100.0,
        pue: parseFloat(pue) || 1.2,
        region: region,
        n_epochs: 1,
      };
    } else {
      inv.inference = {
        gpu: gpuSpec,
        runtime_hours: 8760.0,
        batch_size: 1,
        requests_per_day: parseFloat(requestsPerDay) || 50000.0,
        avg_tokens_per_request: parseInt(tokensPerRequest, 10) || 512,
      };
    }

    return inv;
  }, [
    modelName, modelFamily, paramsBillions, precision, region,
    gpuModel, gpuCount, gpuTdp, mode, durationHours, pue, requestsPerDay, tokensPerRequest
  ]);

  const calculateLedger = useCallback(async () => {
    setCalculating(true);
    setCalcError(null);
    try {
      const inv = buildInventory();
      const res = await api.ledger({ inventory: inv });
      setLedgerData(res);
    } catch (err: any) {
      setCalcError(err.message || 'Error executing ledger calculation on backend');
    } finally {
      setCalculating(false);
    }
  }, [buildInventory]);

  // Initial calculation once metadata is loaded
  useEffect(() => {
    if (meta && !ledgerData && !calculating) {
      calculateLedger();
    }
  }, [meta, ledgerData, calculating, calculateLedger]);

  const currentLedger = ledgerData
    ? boundary === 'operational'
      ? ledgerData.operational
      : ledgerData.full_lifecycle
    : null;

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>AI System Lifecycle Carbon & Energy Auditor</h1>
        <p className={styles.pageSubtitle}>
          Audit dynamic operational energy and amortised full-lifecycle carbon emissions
          under strict empirical accounting with 1,000 Monte Carlo uncertainty iterations.
        </p>
      </header>

      {metaError && (
        <Callout status="error" title="Backend Connection Error">
          {metaError}. Ensure the FastAPI server is running at <code>http://127.0.0.1:8000</code>.
        </Callout>
      )}

      {/* Main Two-Column Layout */}
      <div className={styles.layout}>
        {/* Left Column: System Inventory Inputs Panel */}
        <aside className={styles.inputsPanel}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 className={styles.inputsPanelTitle}>System Inventory</h2>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              Specification
            </span>
          </div>

          {/* Presets Selector */}
          {meta && meta.preset_scenarios && (
            <Select
              label="Preset Scenario Quick-Fill"
              value={selectedPresetId}
              onChange={(e) => handlePresetChange(e.target.value)}
              options={meta.preset_scenarios.map((p) => ({
                value: p.id,
                label: p.name,
              }))}
              helperText="Loads validated configurations from published benchmarks."
            />
          )}

          {/* Model Spec */}
          <div className={styles.sectionDivider}>Model Architecture</div>

          <Input
            label="Model Identifier / Name"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            helperText="e.g. BLOOM-176B, LLaMA-3-8B"
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <Input
              label="Parameters (Billions)"
              mono
              value={paramsBillions}
              onChange={(e) => setParamsBillions(e.target.value)}
              suffix="B"
            />
            <Select
              label="Numerical Precision"
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

          {/* Hardware Spec */}
          <div className={styles.sectionDivider}>Hardware Accelerator</div>

          {meta && (
            <Select
              label="Accelerator Model"
              value={gpuModel}
              onChange={(e) => {
                const val = e.target.value;
                setGpuModel(val);
                const found = meta.hardware.find((h) => h.model === val);
                if (found) setGpuTdp(found.tdp_w.toString());
              }}
              options={meta.hardware.map((h) => ({
                value: h.model,
                label: `${h.model} (${h.tdp_w}W TDP${h.vram_gb ? `, ${h.vram_gb}GB` : ''})`,
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
              label="TDP (Watts/Device)"
              mono
              value={gpuTdp}
              onChange={(e) => setGpuTdp(e.target.value)}
              suffix="W"
            />
          </div>

          {/* Lifecycle Mode & Region */}
          <div className={styles.sectionDivider}>Execution & Environment</div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
            <Select
              label="Execution Phase"
              value={mode}
              onChange={(e) => setMode(e.target.value as any)}
              options={[
                { value: 'training', label: 'Training Run' },
                { value: 'inference', label: 'Inference Serving' },
              ]}
            />
            {meta && (
              <Select
                label="Geographical Region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                options={meta.regions.map((r) => ({
                  value: r.code,
                  label: `${r.name} (${r.intensity_gco2_per_kwh.toFixed(0)} g/kWh)`,
                }))}
              />
            )}
          </div>

          {mode === 'training' ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <Input
                label="Training Duration"
                mono
                value={durationHours}
                onChange={(e) => setDurationHours(e.target.value)}
                suffix="Hours"
              />
              <Input
                label="Facility PUE"
                mono
                value={pue}
                onChange={(e) => setPue(e.target.value)}
                suffix="Ratio"
              />
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
              <Input
                label="Daily Traffic"
                mono
                value={requestsPerDay}
                onChange={(e) => setRequestsPerDay(e.target.value)}
                suffix="Req/day"
              />
              <Input
                label="Tokens per Req"
                mono
                value={tokensPerRequest}
                onChange={(e) => setTokensPerRequest(e.target.value)}
                suffix="Tokens"
              />
            </div>
          )}

          <Button
            variant="primary"
            size="lg"
            onClick={calculateLedger}
            disabled={calculating || metaLoading}
            icon={calculating ? <RefreshCw className={styles.spinner} size={16} /> : <Sliders size={16} />}
          >
            {calculating ? 'Running Monte Carlo...' : 'Compute Lifecycle Ledger'}
          </Button>
        </aside>

        {/* Right Column: Results & Footprint Section */}
        <section className={styles.resultsPanel}>
          {/* Boundary Toggle Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
            <div>
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-xs)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
                Accounting Scope
              </span>
              <div className={styles.boundaryToggle} role="radiogroup" aria-label="Accounting Boundary Scope">
                <button
                  type="button"
                  className={`${styles.boundaryOption} ${boundary === 'operational' ? styles.active : ''}`}
                  onClick={() => setBoundary('operational')}
                  role="radio"
                  aria-checked={boundary === 'operational'}
                >
                  <Layers size={14} />
                  {BOUNDARY_LABELS.operational}
                </button>
                <button
                  type="button"
                  className={`${styles.boundaryOption} ${boundary === 'full_lifecycle' ? styles.active : ''}`}
                  onClick={() => setBoundary('full_lifecycle')}
                  role="radio"
                  aria-checked={boundary === 'full_lifecycle'}
                >
                  <Layers size={14} />
                  {BOUNDARY_LABELS.full_lifecycle}
                </button>
              </div>
            </div>

            {currentLedger && (
              <button
                type="button"
                className={styles.assumptionsLink}
                onClick={() => setDrawerOpen(true)}
              >
                <HelpCircle size={14} />
                Audit Stated Assumptions ({currentLedger.assumptions.monte_carlo_n_samples} MC Runs)
              </button>
            )}
          </div>

          {calcError && (
            <Callout status="error" title="Calculation Failed">
              {calcError}
            </Callout>
          )}

          {calculating && !currentLedger && (
            <div className={styles.spinnerWrapper}>
              <RefreshCw className={styles.spinner} size={24} />
              <span>Simulating 1,000 parameter distributions with Monte Carlo propagation...</span>
            </div>
          )}

          {/* Real Backend Data Display */}
          {currentLedger && (
            <div className={styles.footprintCard}>
              <div className={styles.footprintCardHeader}>
                <h3 className={styles.footprintCardTitle}>
                  {BOUNDARY_LABELS[boundary]} Summary
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  {ledgerData && (
                    <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={<Download size={14} />}
                        onClick={() => exportLedgerToJSON(ledgerData.operational, ledgerData.full_lifecycle)}
                      >
                        JSON
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={<Download size={14} />}
                        onClick={() => exportLedgerToCSV(ledgerData.operational, ledgerData.full_lifecycle)}
                      >
                        CSV
                      </Button>
                    </div>
                  )}
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    Schema v{currentLedger.schema_version}
                  </span>
                </div>
              </div>

              <div className={styles.footprintCardBody}>
                {/* Total Carbon Quantity from Backend */}
                <div className={styles.totalCarbonRow}>
                  <span className={styles.totalLabel}>
                    Total Estimated Carbon Footprint ({boundary === 'operational' ? 'Dynamic Energy Only' : 'Cradle-to-Grave Amortised'})
                  </span>
                  <QuantityDisplay
                    quantity={currentLedger.total_carbon}
                    showSource
                  />
                </div>

                {/* Total Energy Quantity from Backend */}
                <div className={styles.totalCarbonRow}>
                  <span className={styles.totalLabel}>Total Estimated Electricity Consumption</span>
                  <QuantityDisplay
                    quantity={currentLedger.total_energy}
                    showSource
                  />
                </div>

                {/* Component Breakdown from Backend */}
                <span className={styles.totalLabel}>Lifecycle Component Breakdown</span>
                <div className={styles.componentGrid}>
                  <div className={styles.componentRow}>
                    <span className={styles.componentLabel}>Dynamic Training Carbon</span>
                    <QuantityDisplay quantity={currentLedger.training} compact />
                  </div>

                  <div className={styles.componentRow}>
                    <span className={styles.componentLabel}>Runtime Inference Carbon</span>
                    <QuantityDisplay quantity={currentLedger.inference} compact />
                  </div>

                  <div className={styles.componentRow}>
                    <span className={styles.componentLabel}>Embodied Hardware (Manufacturing Amortised)</span>
                    <QuantityDisplay quantity={currentLedger.embodied_hardware} compact />
                  </div>

                  <div className={styles.componentRow}>
                    <span className={styles.componentLabel}>Periodic Retraining Carbon</span>
                    <QuantityDisplay quantity={currentLedger.retraining} compact />
                  </div>

                  <div className={styles.componentRow}>
                    <span className={styles.componentLabel}>Storage Footprint Carbon</span>
                    <QuantityDisplay quantity={currentLedger.storage} compact />
                  </div>

                  <div className={styles.componentRow}>
                    <span className={styles.componentLabel}>Network Ingress/Egress Carbon</span>
                    <QuantityDisplay quantity={currentLedger.network} compact />
                  </div>
                </div>

                {/* Per Request Carbon */}
                <div className={styles.perRequestRow}>
                  <span className={styles.componentLabel}>Carbon Footprint Per Serving Request</span>
                  <QuantityDisplay quantity={currentLedger.per_request} compact />
                </div>
              </div>
            </div>
          )}

          {/* Assumptions Drawer */}
          {currentLedger && (
            <AssumptionsDrawer
              isOpen={drawerOpen}
              onClose={() => setDrawerOpen(false)}
              assumptions={currentLedger.assumptions}
            />
          )}
        </section>
      </div>
    </div>
  );
};
