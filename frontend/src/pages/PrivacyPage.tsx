import React from 'react';

export const PrivacyPage: React.FC = () => {
  return (
    <article style={{ maxWidth: '800px', margin: '0 auto', padding: 'var(--space-8) var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <header style={{ borderBottom: '1px solid var(--color-border-default)', paddingBottom: 'var(--space-4)' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-2xl)' }}>Privacy Notice</h1>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginTop: 'var(--space-1)' }}>
          Sustainable AI Lifecycle Auditor • Transparent Data Processing
        </p>
      </header>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', lineHeight: 1.65 }}>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)' }}>1. Client-Side & Local Computation</h2>
        <p>
          The Sustainable AI Lifecycle Auditor is designed for internal infrastructure auditing and scientific reproducibility. All inventory parameters, server specifications, and model details submitted through this application are processed solely by your designated backend API server instance.
        </p>

        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)' }}>2. Zero User Tracking & Self-Hosted Fonts</h2>
        <p>
          This application does not load external third-party trackers, telemetry scripts, or cookies. All typography assets (Source Serif 4, IBM Plex Sans, IBM Plex Mono) are self-hosted directly on the local web server to eliminate surveillance and external IP logging.
        </p>

        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-lg)' }}>3. LLM Claim Extraction Boundary</h2>
        <p>
          When submitting marketing text or paper snippets for claim extraction, the text is processed via local deterministic pattern-matching fallback by default. If optional Gemini API integration is configured on your server, text snippets are transmitted via encrypted API calls strictly for structured extraction without data retention for model training.
        </p>
      </section>
    </article>
  );
};
