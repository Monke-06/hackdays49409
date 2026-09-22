import React from 'react';
import styles from './Checkbox.module.css';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  description?: string;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  label,
  description,
  id,
  className = '',
  ...props
}) => {
  const checkboxId = id || `cb-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <label htmlFor={checkboxId} className={`${styles.container} ${className}`}>
      <input
        type="checkbox"
        id={checkboxId}
        className={styles.checkbox}
        {...props}
      />
      <div className={styles.textWrapper}>
        <span className={styles.label}>{label}</span>
        {description && <span className={styles.description}>{description}</span>}
      </div>
    </label>
  );
};
