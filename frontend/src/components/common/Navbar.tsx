import React, { useEffect, useState } from 'react';
import { api, type HealthResponse } from '../../api/client';
import styles from './Navbar.module.css';

export interface NavbarProps {
  currentRoute: string;
  onRouteChange: (route: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentRoute, onRouteChange }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    let mounted = true;
    api.health()
      .then((h) => {
        if (mounted) setHealth(h);
      })
      .catch(() => {
        if (mounted) setHealthError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <header className={styles.navbar}>
      <div className={styles.brand}>
        <span className={styles.brandTitle}>Sustainable AI Lifecycle Auditor</span>
      </div>

      <nav className={styles.navLinks} aria-label="Main Navigation">
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'ledger' ? styles.active : ''}`}
          onClick={() => onRouteChange('ledger')}
        >
          Lifecycle Ledger
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'recommender' ? styles.active : ''}`}
          onClick={() => onRouteChange('recommender')}
        >
          Recommender
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'claims' ? styles.active : ''}`}
          onClick={() => onRouteChange('claims')}
        >
          Claim Verifier
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'methodology' ? styles.active : ''}`}
          onClick={() => onRouteChange('methodology')}
        >
          Methodology
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'inventory-parse' ? styles.active : ''}`}
          onClick={() => onRouteChange('inventory-parse')}
        >
          Parse Config
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'self-footprint' ? styles.active : ''}`}
          onClick={() => onRouteChange('self-footprint')}
        >
          Self Footprint
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'privacy' ? styles.active : ''}`}
          onClick={() => onRouteChange('privacy')}
        >
          Privacy
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'terms' ? styles.active : ''}`}
          onClick={() => onRouteChange('terms')}
        >
          Terms
        </button>
        <button
          type="button"
          className={`${styles.navLink} ${currentRoute === 'design' ? styles.active : ''}`}
          onClick={() => onRouteChange('design')}
        >
          Specimen (Dev)
        </button>
      </nav>

      <div className={styles.statusIndicator} title={healthError ? 'Backend offline' : `Backend API v${health?.version || '1.0.0'}`}>
        <span
          className={`${styles.statusDot} ${healthError ? styles.error : ''}`}
          aria-hidden="true"
        />
        <span>{healthError ? 'API Disconnected' : `v${health?.version || '1.0.0'} Connected`}</span>
      </div>
    </header>
  );
};
