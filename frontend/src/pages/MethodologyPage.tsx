import React from 'react';
import { Table } from '../components/base';
import styles from './MethodologyPage.module.css';

export const MethodologyPage: React.FC = () => {
  return (
    <article className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Methodology & Empirical Accounting Framework</h1>
        <p className={styles.pageSubtitle}>
          How the Sustainable AI Lifecycle Auditor derives carbon and energy quantities, propagates uncertainty, detects boundary shifts, and cancels ambient errors in comparative paired Monte Carlo trials.
        </p>
      </header>

      {/* Section 1: Dual-Boundary Accounting */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>1. Dual-Boundary Accounting Principle</h2>
        <p className={styles.paragraph}>
          AI efficiency claims routinely commit boundary shifting: declaring a model &ldquo;40% greener&rdquo; by measuring only runtime inference electricity while omitting the massive embodied carbon of accelerator manufacturing, or ignoring one-time distillation and pre-training overhead.
        </p>
        <p className={styles.paragraph}>
          To prevent deceptive accounting, every system is evaluated under two strictly defined scopes:
        </p>
        <div className={styles.mathBlock}>
          <div><strong>Scope A: Operational Boundary</strong></div>
          <div>Total Carbon = Dynamic Inference Carbon + Dynamic Training Energy Carbon</div>
          <div>E_op (kWh) = (Power_TDP &times; Utilization &times; Runtime_hours &times; PUE) / 1000</div>
          <br />
          <div><strong>Scope B: Full Lifecycle Boundary (Cradle-to-Grave)</strong></div>
          <div>Total Carbon = Dynamic Energy + Embodied Hardware (Amortised) + Periodic Retraining + Storage + Network</div>
          <div>C_embodied = Hardware_LCA_Total &times; (Runtime_hours / (Hardware_Lifetime_Years &times; 8760))</div>
        </div>
      </section>

      {/* Section 2: Paired Monte Carlo Error Cancellation */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. Paired Monte Carlo Error Cancellation</h2>
        <p className={styles.paragraph}>
          Independent parameter sampling produces misleadingly wide confidence intervals when comparing baseline and subject configurations. For example, if both models execute in the same datacentre region (e.g. France with average 57.0 gCO&#8322;e/kWh), the regional grid carbon intensity fluctuated by &plusmn;20% affects both systems symmetrically.
        </p>
        <p className={styles.paragraph}>
          As implemented in <code>backend/claims/checker.py</code> (function <code>compute_paired_relative_change_mc</code>), our auditor employs <strong>paired Monte Carlo trials</strong> (2,000 samples, fixed random seed):
        </p>

        <div className={styles.tableCard}>
          <Table<{ param: string; dist: string; pairing: string }>
            columns={[
              { header: 'Physical Parameter', accessor: 'param' },
              { header: 'Stated Distribution', accessor: 'dist' },
              { header: 'Paired Cancellation Behavior', accessor: 'pairing' },
            ]}
            data={[
              {
                param: 'Grid Carbon Intensity',
                dist: 'Uniform(0.80, 1.20) [±20%]',
                pairing: 'Cancels: Shared random draw when base and subject share the same geographical region.',
              },
              {
                param: 'Facility PUE',
                dist: 'Uniform(0.90, 1.10) [±10%]',
                pairing: 'Cancels: Shared random draw when base and subject share identical datacentre cooling PUE.',
              },
              {
                param: 'Hardware Silicon Tolerance',
                dist: 'Uniform(0.975, 1.025) [±2.5%]',
                pairing: 'Independent: Separate draws hw_b and hw_s for baseline and subject accelerators.',
              },
            ]}
            keyExtractor={(d) => d.param}
          />
        </div>

        <p className={styles.paragraph}>
          <strong>Why absolute ranges remain wide:</strong> Under <code>backend/ledger/uncertainty.py</code>, an individual system&rsquo;s absolute carbon footprint compounds TDP uncertainty (&plusmn;15%), datacentre PUE (&plusmn;10%), grid carbon variance (&plusmn;20%), and Boavizta LCA manufacturing ranges, creating an absolute 5th&ndash;95th percentile spread of &plusmn;35&ndash;45%. However, in relative comparative claims (Subject &minus; Baseline) / Baseline, shared ambient factors cancel out, allowing rigorous detection of true statistical improvements down to &plusmn;3&ndash;5%.
        </p>
      </section>

      {/* Section 3: Verification Cascade */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>3. Multi-Tier Verification Cascade</h2>
        <p className={styles.paragraph}>
          Claims are vetted through a 3-tier deterministic cascade:
        </p>
        <div className={styles.mathBlock}>
          <div>Tier 1: Boundary &amp; Definition Check</div>
          <div>  - Flags boundary shifting (e.g. claiming full lifecycle savings based only on operational energy).</div>
          <div>Tier 2: Metric &amp; Unit Alignment</div>
          <div>  - Verifies whether claimed metric (energy, carbon, latency) matches computed ledger quantities.</div>
          <div>Tier 3: Paired Statistical Hypothesis Test</div>
          <div>  - Evaluates whether the claimed percentage improvement falls within the [5th, 95th] paired percentile interval.</div>
        </div>
      </section>

      {/* Section 4: Provenance & Data Sources */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>4. Authoritative Empirical Data Sources</h2>
        <p className={styles.paragraph}>
          All numbers are derived from verified third-party empirical datasets:
        </p>
        <ul style={{ paddingLeft: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)' }}>
          <li><strong>Grid Carbon Intensities:</strong> Ember Global Electricity Review (2024), CC BY 4.0.</li>
          <li><strong>Embodied Hardware Carbon:</strong> Boavizta open-source hardware life cycle assessment database (v1.0), including server chassis and GPU die manufacturing footprints.</li>
          <li><strong>Dynamic Energy Modeling:</strong> Lannelongue et al. (2021) Green Algorithms formula, Advanced Science 8(12).</li>
        </ul>
      </section>
    </article>
  );
};
