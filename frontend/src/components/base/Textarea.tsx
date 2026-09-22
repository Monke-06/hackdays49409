import React from 'react';
import styles from './Textarea.module.css';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  optional?: boolean;
  helperText?: string;
  error?: string;
  mono?: boolean;
}

export const Textarea: React.FC<TextareaProps> = ({
  label,
  optional,
  helperText,
  error,
  mono,
  className = '',
  id,
  ...props
}) => {
  const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={styles.container}>
      {label && (
        <label htmlFor={textareaId} className={styles.label}>
          {label}
          {optional && <span className={styles.labelOptional}>(Optional)</span>}
        </label>
      )}
      <textarea
        id={textareaId}
        className={`${styles.textarea} ${mono ? styles.mono : ''} ${error ? styles.textareaError : ''} ${className}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${textareaId}-error` : helperText ? `${textareaId}-helper` : undefined}
        {...props}
      />
      {error ? (
        <span id={`${textareaId}-error`} className={styles.errorText} role="alert">
          {error}
        </span>
      ) : helperText ? (
        <span id={`${textareaId}-helper`} className={styles.helperText}>
          {helperText}
        </span>
      ) : null}
    </div>
  );
};
