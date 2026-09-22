import React from 'react';
import { Info, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';
import styles from './Callout.module.css';

export interface CalloutProps {
  status?: 'info' | 'success' | 'warning' | 'error' | 'neutral';
  title?: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const Callout: React.FC<CalloutProps> = ({
  status = 'info',
  title,
  children,
  icon,
  className = '',
}) => {
  const defaultIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle2 size={18} />;
      case 'warning':
        return <AlertTriangle size={18} />;
      case 'error':
        return <AlertCircle size={18} />;
      case 'info':
      case 'neutral':
      default:
        return <Info size={18} />;
    }
  };

  return (
    <div className={`${styles.callout} ${styles[status]} ${className}`} role="status">
      <div className={styles.icon} aria-hidden="true">
        {icon || defaultIcon()}
      </div>
      <div className={styles.content}>
        {title && <div className={styles.title}>{title}</div>}
        <div className={styles.description}>{children}</div>
      </div>
    </div>
  );
};
