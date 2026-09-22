import React from 'react';

export const TermsPage: React.FC = () => {
  return (
    <article style={{ maxWidth: '800px', margin: '0 auto', padding: 'var(--space-8) var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <header style={{ borderBottom: '1px solid var(--color-border-default)', paddingBottom: 'var(--space-4)' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-2xl)' }}>Terms of Service & Scientific Disclaimers</h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--space-1)' }}>
          Sustainable AI Lifecycle Auditor • Academic and Commercial Use
        </p>
      </header>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', lineHeight: 1.65 }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)' }}>1. Stated Assumptions Enclosure</h2>
        <p>
          All numerical estimates, carbon quantities, energy metrics, and break-even crossover points provided by this tool carry explicit 5th–95th percentile confidence intervals under stated physical assumptions. Changing grid regional coefficients, cooling PUE, or GPU utilization moves real-world results outside these modeled envelopes.
        </p>

        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)' }}>2. Anti-Greenwashing Disclaimer</h2>
        <p>
          The Recommender and Claim Verifier tools provide objective mathematical audits based on published empirical parameters. They do not constitute certified regulatory carbon credits, legal tax declarations, or statutory ESG compliance filings without independent third-party physical telemetry verification.
        </p>

        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)' }}>3. Open Licenses</h2>
        <p>
          Grid carbon datasets are provided under Creative Commons Attribution 4.0 International (CC BY 4.0) via Ember. Embedded hardware LCA datasets are sourced from Boavizta open data. Typography is licensed under the SIL Open Font License 1.1.
        </p>
      </section>
    </article>
  );
};
