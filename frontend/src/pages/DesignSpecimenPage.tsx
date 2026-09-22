import React, { useState } from 'react';
import {
  Button,
  Input,
  Select,
  Textarea,
  Checkbox,
  Card,
  Callout,
  Table,
  SourceMarker,
  Drawer,
} from '../components/base';
import { Check, RefreshCw } from 'lucide-react';
import styles from './DesignSpecimenPage.module.css';

interface TableSpecimenRow {
  id: string;
  name: string;
  architecture: string;
  throughput: string;
  envelope: string;
  status: string;
}

const TABLE_SPECIMEN_DATA: TableSpecimenRow[] = [
  {
    id: 'spec-01',
    name: 'Specimen Alpha Reference',
    architecture: 'Standard Tensor Cluster',
    throughput: '1,420 tokens/sec',
    envelope: '± 12.4% CI',
    status: 'Nominal Baseline',
  },
  {
    id: 'spec-02',
    name: 'Specimen Beta Quantized',
    architecture: 'Reduced Precision Pipeline',
    throughput: '2,890 tokens/sec',
    envelope: '± 4.8% CI',
    status: 'High Efficiency',
  },
  {
    id: 'spec-03',
    name: 'Specimen Gamma Accelerated',
    architecture: 'Specialized Coprocessor',
    throughput: '3,110 tokens/sec',
    envelope: '± 7.2% CI',
    status: 'Alternative Host',
  },
  {
    id: 'spec-04',
    name: 'Specimen Delta Distilled',
    architecture: 'Compact Student Model',
    throughput: '4,650 tokens/sec',
    envelope: '± 15.1% CI',
    status: 'Constrained Bound',
  },
];

export const DesignSpecimenPage: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [checkboxState, setCheckboxState] = useState(true);
  const [inputText, setInputText] = useState('Placeholder Sample Input');
  const [selectVal, setSelectVal] = useState('opt-fra');

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.badgeDev}>Dev Environment Only • Specimen Preview</div>
        <h1 className={styles.title}>Design System & Component Specimen Sheet</h1>
        <p className={styles.subtitle}>
          Visual test harness and verification sheet demonstrating typography, design tokens,
          accessibility contrast, and base components using non-data placeholder text.
        </p>
      </header>

      {/* 1. Typography Hierarchy */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>1. Typography & Hierarchy (Self-Hosted OFL)</h2>
          <p className={styles.sectionDesc}>
            Source Serif 4 for editorial headlines; IBM Plex Sans for UI and forms; IBM Plex Mono for technical quantities.
          </p>
        </div>

        <div className={styles.grid2}>
          <div className={styles.typeSample}>
            <span className={styles.typeMeta}>Source Serif 4 • 4xl (3rem / 48px) SemiBold</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-4xl)', lineHeight: 'var(--line-height-4xl)', fontWeight: 600 }}>
              Rigorous Empirical Auditing
            </div>
            <span className={styles.typeMeta}>Source Serif 4 • 2xl (1.875rem / 30px) SemiBold</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-2xl)', lineHeight: 'var(--line-height-2xl)', fontWeight: 600 }}>
              Dual-Boundary Accounting Methodology
            </div>
            <span className={styles.typeMeta}>Source Serif 4 • lg (1.25rem / 20px) Regular Italic</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)', lineHeight: 'var(--line-height-lg)', fontStyle: 'italic' }}>
              “Sphinx of black quartz, judge my vow under stated assumptions.”
            </div>
          </div>

          <div className={styles.typeSample}>
            <span className={styles.typeMeta}>IBM Plex Sans • Body Base (1rem / 16px) Regular</span>
            <p style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-base)', lineHeight: 'var(--line-height-base)' }}>
              All estimates are bounded by stated uncertainty envelopes. Comparative evaluation between baseline
              and subject configurations cancels shared ambient parameters while maintaining independent hardware tolerances.
            </p>
            <span className={styles.typeMeta}>IBM Plex Mono • Technical Parameters (0.875rem / 14px)</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', backgroundColor: 'var(--color-bg-subtle)', padding: 'var(--space-2)', borderRadius: 'var(--radius-sm)' }}>
              <div>Nominal TDP: 400.0 W (±15% tolerance)</div>
              <div>Sample Interval: [5th: 24.69, 95th: 29.75] kgCO2e</div>
              <div>Break-even Point: 1,280,000 requests</div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Color Tokens & Source Markers */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>2. Semantic Tokens & Source Markers</h2>
          <p className={styles.sectionDesc}>
            High-contrast color tokens paired for WCAG AAA compliance. Extraction sources use plain text with a small square marker.
          </p>
        </div>

        <div className={styles.grid2}>
          <div>
            <h3 style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: 'var(--space-2)' }}>
              Extraction Source Markers (Plain Text + Square Marker)
            </h3>
            <div className={styles.markerRow}>
              <SourceMarker source="gemini" />
              <SourceMarker source="rules_fallback" />
              <SourceMarker source="user_specified" />
            </div>
          </div>

          <div>
            <h3 style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-sm)', fontWeight: 600, marginBottom: 'var(--space-2)' }}>
              Palette Swatches
            </h3>
            <div className={styles.swatchGrid}>
              <div className={styles.swatch}>
                <div className={styles.swatchColor} style={{ backgroundColor: 'var(--color-text-primary)' }} />
                <div className={styles.swatchInfo}>
                  <span className={styles.swatchName}>Text Primary</span>
                  <span className={styles.swatchHex}>#0F172A (17.5:1)</span>
                </div>
              </div>
              <div className={styles.swatch}>
                <div className={styles.swatchColor} style={{ backgroundColor: 'var(--color-status-success-bg)', borderBottom: '2px solid var(--color-status-success-border)' }} />
                <div className={styles.swatchInfo}>
                  <span className={styles.swatchName}>Success Pair</span>
                  <span className={styles.swatchHex}>#14532D on #F0FDF4</span>
                </div>
              </div>
              <div className={styles.swatch}>
                <div className={styles.swatchColor} style={{ backgroundColor: 'var(--color-status-warning-bg)', borderBottom: '2px solid var(--color-status-warning-border)' }} />
                <div className={styles.swatchInfo}>
                  <span className={styles.swatchName}>Warning Pair</span>
                  <span className={styles.swatchHex}>#7C2D12 on #FFF7ED</span>
                </div>
              </div>
              <div className={styles.swatch}>
                <div className={styles.swatchColor} style={{ backgroundColor: 'var(--color-status-error-bg)', borderBottom: '2px solid var(--color-status-error-border)' }} />
                <div className={styles.swatchInfo}>
                  <span className={styles.swatchName}>Error Pair</span>
                  <span className={styles.swatchHex}>#7F1D1D on #FEF2F2</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Interactive Base Components */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>3. Interactive Form & Button Controls</h2>
          <p className={styles.sectionDesc}>
            All UI labels use human-readable text. Tested across default, hover, focus-visible, and disabled states.
          </p>
        </div>

        <div className={styles.grid2}>
          <div className={styles.specimenCard}>
            <h3 style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
              Button Variants & Sizes
            </h3>
            <div className={styles.controlsRow}>
              <Button variant="primary" size="md" icon={<Check size={16} />}>Primary Action</Button>
              <Button variant="secondary" size="md" icon={<RefreshCw size={16} />}>Secondary Action</Button>
              <Button variant="danger" size="md">Danger Action</Button>
              <Button variant="ghost" size="md">Ghost Link</Button>
            </div>
            <div className={styles.controlsRow}>
              <Button variant="primary" size="sm">Small (28px)</Button>
              <Button variant="primary" size="md">Medium (36px)</Button>
              <Button variant="primary" size="lg">Large (44px)</Button>
              <Button variant="primary" size="md" disabled>Disabled State</Button>
            </div>
          </div>

          <div className={styles.specimenCard}>
            <h3 style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--font-size-sm)', fontWeight: 600 }}>
              Form Input Controls
            </h3>
            <Input
              label="Standard Text Parameter"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              helperText="Human-readable parameter description."
            />
            <Input
              label="Monospace Numeric Input"
              mono
              value="400.0"
              suffix="Watts TDP"
              helperText="Validated thermal design power."
            />
            <Select
              label="Geographical Power Grid Region"
              value={selectVal}
              onChange={(e) => setSelectVal(e.target.value)}
              options={[
                { value: 'opt-fra', label: 'France (Jean Zay Cluster - 57.0 gCO2e/kWh)' },
                { value: 'opt-deu', label: 'Germany (National Average - 380.0 gCO2e/kWh)' },
                { value: 'opt-usa', label: 'United States (National Grid - 415.0 gCO2e/kWh)' },
                { value: 'opt-nor', label: 'Norway (Hydropower Region - 28.0 gCO2e/kWh)' },
              ]}
              helperText="Determines carbon intensity coefficient."
            />
            <Checkbox
              label="Enable Amortized Embodied Hardware Boundary"
              description="Includes manufacturing and supply chain overheads."
              checked={checkboxState}
              onChange={(e) => setCheckboxState(e.target.checked)}
            />
          </div>
        </div>
      </section>

      {/* 4. Feedback & Status Callouts */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>4. Status & Verification Callouts</h2>
          <p className={styles.sectionDesc}>
            Structured feedback alerts for boundary shifts, validation successes, and binding constraints.
          </p>
        </div>

        <div className={styles.grid2}>
          <Callout status="info" title="Under Stated Assumptions">
            All numerical ranges are generated via 1,000 Monte Carlo propagation trials under explicit parameters.
          </Callout>
          <Callout status="success" title="Claim Empirically Supported">
            Both operational and full-lifecycle evaluations confirm the stated efficiency improvement.
          </Callout>
          <Callout status="warning" title="Boundary Shift Detected">
            The published claim compares operational energy against a full lifecycle baseline.
          </Callout>
          <Callout status="error" title="Binding Constraint Binding">
            All candidates exceed the strict latency constraint (minimum observed latency: 450.0 ms).
          </Callout>
        </div>
      </section>

      {/* 5. Data Table Specimen */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>5. Structured Scientific Table Specimen</h2>
          <p className={styles.sectionDesc}>
            Data-dense presentation format for architecture comparison, ledger breakdowns, and verification steps.
          </p>
        </div>

        <Table<TableSpecimenRow>
          columns={[
            { header: 'Specimen Label', accessor: 'name' },
            { header: 'Processor Architecture', accessor: 'architecture' },
            { header: 'Throughput', accessor: 'throughput', align: 'right', mono: true },
            { header: 'Uncertainty Interval', accessor: 'envelope', align: 'right', mono: true },
            { header: 'Verification Status', accessor: 'status' },
          ]}
          data={TABLE_SPECIMEN_DATA}
          keyExtractor={(r) => r.id}
        />
      </section>

      {/* 6. Cards & Drawer Specimen */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>6. Cards & Auditing Drawer Specimen</h2>
          <p className={styles.sectionDesc}>
            Modal slide-out panel for auditing underlying parameter assumptions and citations.
          </p>
        </div>

        <div className={styles.grid3}>
          <Card
            variant="default"
            title="Default Specimen Card"
            subtitle="Base container border"
            footer={<Button size="sm" variant="secondary">View Ledger</Button>}
          >
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
              Standard surface card used for primary dashboard widgets and inventory forms.
            </p>
          </Card>

          <Card
            variant="subtle"
            title="Subtle Specimen Card"
            subtitle="Subdued surface background"
            footer={<Button size="sm" variant="secondary">Inspect</Button>}
          >
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
              Subdued card used for secondary data groupings or metadata notes.
            </p>
          </Card>

          <Card
            variant="raised"
            title="Raised Specimen Card"
            subtitle="Elevated surface with shadow"
            footer={<Button size="sm" variant="primary" onClick={() => setDrawerOpen(true)}>Open Drawer</Button>}
          >
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
              Elevated card for highlighted recommendations and active comparisons.
            </p>
          </Card>
        </div>

        {/* Drawer Component Demo */}
        <Drawer
          isOpen={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          title="Auditing Assumptions Inspector"
          footer={
            <>
              <Button variant="secondary" size="md" onClick={() => setDrawerOpen(false)}>Dismiss</Button>
              <Button variant="primary" size="md" onClick={() => setDrawerOpen(false)}>Export Audit Data</Button>
            </>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <Callout status="info" title="Auditing Principle">
              Every numerical quantity displayed is derived from explicit physical or modeled parameters.
            </Callout>
            <Input label="Datacenter Power Usage Effectiveness (PUE)" mono value="1.20" suffix="Jean Zay facility" />
            <Input label="Hardware Manufacturing Lifetime" mono value="4.0" suffix="Years amortized" />
            <Input label="Monte Carlo Iteration Count" mono value="1,000" suffix="Runs (Seed: 42)" />
            <Textarea label="Methodology Citation Notes" value="Based on Luccioni et al. (2023) and Boavizta bottom-up LCA database." />
          </div>
        </Drawer>
      </section>

      {/* 7. Motion & Accessibility Specimen */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>7. Motion Specification & Accessibility</h2>
          <p className={styles.sectionDesc}>
            Motion is purely functional with zero decorative count-up delays. Complies with user preference for reduced motion.
          </p>
        </div>

        <Callout status="neutral" title="Reduced Motion Policy Enforced">
          When <code>prefers-reduced-motion: reduce</code> is signaled by the browser or operating system,
          all drawer slides, modal dissolves, and hover transitions are converted to instant state changes (0.01ms duration).
        </Callout>
      </section>
    </div>
  );
};
