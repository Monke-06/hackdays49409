import React from 'react';
import styles from './Input.module.css';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  optional?: boolean;
  helperText?: string;
  error?: string;
  suffix?: string;
  mono?: boolean;
}

export const Input: React.FC<InputProps> = ({
  label,
  optional,
  helperText,
  error,
  suffix,
  mono,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={styles.container}>
      {label && (
        <label htmlFor={inputId} className={styles.label}>
          {label}
          {optional && <span className={styles.labelOptional}>(Optional)</span>}
        </label>
      )}
      <div className={styles.inputWrapper}>
        <input
          id={inputId}
          className={`${styles.input} ${mono ? styles.mono : ''} ${error ? styles.inputError : ''} ${className}`}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          {...props}
        />
        {suffix && <span className={styles.suffix}>{suffix}</span>}
      </div>
      {error ? (
        <span id={`${inputId}-error`} className={styles.errorText} role="alert">
          {error}
        </span>
      ) : helperText ? (
        <span id={`${inputId}-helper`} className={styles.helperText}>
          {helperText}
        </span>
      ) : null}
    </div>
  );
};
