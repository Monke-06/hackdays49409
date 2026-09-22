import React from 'react';
import { ChevronDown } from 'lucide-react';
import styles from './Select.module.css';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  optional?: boolean;
  options: SelectOption[];
  helperText?: string;
  error?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  optional,
  options,
  helperText,
  error,
  className = '',
  id,
  ...props
}) => {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={styles.container}>
      {label && (
        <label htmlFor={selectId} className={styles.label}>
          {label}
          {optional && <span className={styles.labelOptional}>(Optional)</span>}
        </label>
      )}
      <div className={styles.selectWrapper}>
        <select
          id={selectId}
          className={`${styles.select} ${error ? styles.selectError : ''} ${className}`}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${selectId}-error` : helperText ? `${selectId}-helper` : undefined}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className={styles.arrow} aria-hidden="true">
          <ChevronDown size={16} />
        </span>
      </div>
      {error ? (
        <span id={`${selectId}-error`} className={styles.errorText} role="alert">
          {error}
        </span>
      ) : helperText ? (
        <span id={`${selectId}-helper`} className={styles.helperText}>
          {helperText}
        </span>
      ) : null}
    </div>
  );
};
