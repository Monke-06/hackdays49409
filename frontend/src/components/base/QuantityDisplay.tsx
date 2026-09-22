/**
 * QuantityDisplay
 *
 * Renders a Quantity from the API with:
 *  - value + unit (from API, never hardcoded)
 *  - low–high range (from API, under stated assumptions)
 *  - tier tag ("Measured" or "Modelled") from API tier field
 *  - optional source attribution
 *
 * Never invents or formats numbers. All values come directly from the Quantity object.
 */
import React from 'react';
import type { Quantity } from '../../api/client';
import { TIER_LABELS } from '../../api/labels';
import styles from './QuantityDisplay.module.css';

export interface QuantityDisplayProps {
  quantity: Quantity;
  compact?: boolean;
  showSource?: boolean;
  label?: string;
}

function formatNumber(n: number): string {
  if (Math.abs(n) >= 1_000_000) return n.toLocaleString('en-GB', { maximumFractionDigits: 0 });
  if (Math.abs(n) >= 1_000)     return n.toLocaleString('en-GB', { maximumFractionDigits: 1 });
  if (Math.abs(n) >= 10)        return n.toLocaleString('en-GB', { maximumFractionDigits: 2 });
  return n.toLocaleString('en-GB', { maximumFractionDigits: 4 });
}

export const QuantityDisplay: React.FC<QuantityDisplayProps> = ({
  quantity,
  compact = false,
  showSource = false,
}) => {
  const tierLabel = TIER_LABELS[quantity.tier] ?? quantity.tier;

  return (
    <div className={`${styles.row} ${compact ? styles.compact : ''}`}>
      <div className={styles.topLine}>
        <span className={styles.value}>{formatNumber(quantity.value)}</span>
        <span className={styles.unit}>{quantity.unit}</span>
        <span className={`${styles.tier} ${styles[quantity.tier]}`}>
          {tierLabel}
        </span>
      </div>
      <div className={styles.range}>
        Range: {formatNumber(quantity.low)} – {formatNumber(quantity.high)} {quantity.unit} (5th–95th percentile, under stated assumptions)
      </div>
      {showSource && (
        <div className={styles.source}>{quantity.source}</div>
      )}
    </div>
  );
};
