import React from 'react';
import { Drawer, QuantityDisplay } from '../base';
import type { LedgerAssumptions } from '../../api/client';
import { ACCOUNTING_LABELS } from '../../api/labels';
import styles from './AssumptionsDrawer.module.css';

interface Field {
  label: string;
  value: React.ReactNode;
  note?: string;
}

interface AssumptionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  assumptions: LedgerAssumptions;
}

export const AssumptionsDrawer: React.FC<AssumptionsDrawerProps> = ({
  isOpen,
  onClose,
  assumptions,
}) => {
  const fields: Field[] = [
    {
      label: 'Grid Carbon Intensity',
      value: (
        <QuantityDisplay
          quantity={assumptions.grid_intensity_gco2_per_kwh}
          compact
          showSource
        />
      ),
      note: 'Source: Ember Global Electricity Review 2024, CC BY 4.0',
    },
    {
      label: 'Power Usage Effectiveness (PUE)',
      value: <span className={styles.fieldValue}>{assumptions.pue.toFixed(2)}</span>,
      note: assumptions.pue_source,
    },
    {
      label: 'GPU Utilisation Fraction',
      value: (
        <span className={styles.fieldValue}>
          {(assumptions.utilization * 100).toFixed(0)}% of peak TDP
        </span>
      ),
      note: assumptions.utilization_source,
    },
    {
      label: 'Hardware Lifetime (Amortisation Period)',
      value: (
        <span className={styles.fieldValue}>
          {assumptions.hardware_lifetime_years} years
        </span>
      ),
      note: assumptions.hardware_lifetime_source,
    },
    {
      label: 'Region',
      value: <span className={styles.fieldValue}>{assumptions.region}</span>,
    },
    {
      label: 'Accounting Method',
      value: (
        <span className={styles.fieldValue}>
          {ACCOUNTING_LABELS[assumptions.accounting] ?? assumptions.accounting}
        </span>
      ),
      note: 'Location-based: uses average grid intensity for the region.',
    },
    {
      label: 'Monte Carlo Samples',
      value: (
        <span className={styles.fieldValue}>
          {assumptions.monte_carlo_n_samples.toLocaleString('en-GB')} samples, seed {assumptions.monte_carlo_seed}
        </span>
      ),
      note: 'Used to propagate uncertainty through TDP ±15%, PUE ±10%, grid intensity ±20%.',
    },
  ];

  return (
    <Drawer isOpen={isOpen} onClose={onClose} title="Stated Assumptions Inspector">
      <div className={styles.noteBanner}>
        {assumptions.note}
      </div>
      {fields.map((f) => (
        <div key={f.label} className={styles.field}>
          <div className={styles.fieldLabel}>{f.label}</div>
          <div>{f.value}</div>
          {f.note && <div className={styles.fieldNote}>{f.note}</div>}
        </div>
      ))}
    </Drawer>
  );
};
