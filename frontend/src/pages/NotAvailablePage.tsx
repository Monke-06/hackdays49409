import React from 'react';
import { Button, Callout } from '../components/base';
import { Construction, ArrowLeft } from 'lucide-react';

export interface NotAvailablePageProps {
  featureName: string;
  description: string;
  onBack: () => void;
}

export const NotAvailablePage: React.FC<NotAvailablePageProps> = ({
  featureName,
  description,
  onBack,
}) => {
  return (
    <div style={{
      maxWidth: '680px',
      margin: 'var(--space-12) auto',
      padding: 'var(--space-6)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      textAlign: 'center',
      gap: 'var(--space-5)',
    }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--color-bg-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--color-text-secondary)',
      }}>
        <Construction size={28} />
      </div>

      <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--font-size-2xl)' }}>
        {featureName} — Feature Not Available
      </h1>

      <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
        {description}
      </p>

      <Callout status="neutral" title="Implementation Status">
        This capability is scheduled for backend v1.1.0 release. The current system provides full lifecycle ledger calculation, architecture recommendation with Pareto frontiers, and multi-tier claim auditing.
      </Callout>

      <Button variant="secondary" onClick={onBack} icon={<ArrowLeft size={16} />}>
        Return to Lifecycle Ledger
      </Button>
    </div>
  );
};
