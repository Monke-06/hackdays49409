import React, { useState } from 'react';
import { Navbar } from './components/common/Navbar';
import { LedgerPage } from './pages/LedgerPage';
import { RecommenderPage } from './pages/RecommenderPage';
import { ClaimAuditorPage } from './pages/ClaimAuditorPage';
import { MethodologyPage } from './pages/MethodologyPage';
import { NotAvailablePage } from './pages/NotAvailablePage';
import { PrivacyPage } from './pages/PrivacyPage';
import { TermsPage } from './pages/TermsPage';
import { DesignSpecimenPage } from './pages/DesignSpecimenPage';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<string>('ledger');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--color-bg-canvas)' }}>
      <Navbar currentRoute={currentRoute} onRouteChange={setCurrentRoute} />
      <main style={{ flex: 1 }}>
        {currentRoute === 'ledger' && <LedgerPage />}
        {currentRoute === 'recommender' && <RecommenderPage />}
        {currentRoute === 'claims' && <ClaimAuditorPage />}
        {currentRoute === 'methodology' && <MethodologyPage />}
        {currentRoute === 'inventory-parse' && (
          <NotAvailablePage
            featureName="System Inventory Config Parser"
            description="Automated parsing of Slurm job scripts, Kubernetes manifests, and PyTorch training configs into structured inventories is currently under development."
            onBack={() => setCurrentRoute('ledger')}
          />
        )}
        {currentRoute === 'self-footprint' && (
          <NotAvailablePage
            featureName="Self-Footprint Realtime Telemetry"
            description="Hardware IPMI and NVIDIA NVML physical power monitoring for the auditor server itself is currently in development."
            onBack={() => setCurrentRoute('ledger')}
          />
        )}
        {currentRoute === 'privacy' && <PrivacyPage />}
        {currentRoute === 'terms' && <TermsPage />}
        {currentRoute === 'design' && <DesignSpecimenPage />}
      </main>
    </div>
  );
};

export default App;
