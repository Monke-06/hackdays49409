import React from 'react';
import styles from './SourceMarker.module.css';

export type ExtractionSource = 'gemini' | 'rules_fallback' | 'user_specified';

export interface SourceMarkerProps {
  source: ExtractionSource;
  className?: string;
}

const SOURCE_LABELS: Record<ExtractionSource, string> = {
  gemini: 'Gemini (LLM Extraction)',
  rules_fallback: 'Deterministic Rules Fallback',
  user_specified: 'User Specified Configuration',
};

const SOURCE_CLASS: Record<ExtractionSource, string> = {
  gemini: styles.gemini,
  rules_fallback: styles.rulesFallback,
  user_specified: styles.userSpecified,
};

export const SourceMarker: React.FC<SourceMarkerProps> = ({ source, className = '' }) => {
  const label = SOURCE_LABELS[source] || source;
  const markerClass = SOURCE_CLASS[source] || styles.userSpecified;

  return (
    <span className={`${styles.container} ${className}`} title={`Extraction Source: ${label}`}>
      <span className={`${styles.squareMarker} ${markerClass}`} aria-hidden="true" />
      <span className={styles.text}>{label}</span>
    </span>
  );
};
