import type { LifecycleLedger } from '../api/client';

export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportLedgerToJSON(operational: LifecycleLedger, fullLifecycle: LifecycleLedger) {
  const data = {
    generated_at: new Date().toISOString(),
    operational_boundary: operational,
    full_lifecycle_boundary: fullLifecycle,
  };
  downloadFile(JSON.stringify(data, null, 2), 'lifecycle_ledger_audit.json', 'application/json');
}

export function exportLedgerToCSV(operational: LifecycleLedger, fullLifecycle: LifecycleLedger) {
  const rows = [
    ['Scope', 'Component', 'Value', 'Unit', 'Range Low', 'Range High', 'Tier', 'Source'],
    ['Operational', 'Total Carbon', operational.total_carbon.value, operational.total_carbon.unit, operational.total_carbon.low, operational.total_carbon.high, operational.total_carbon.tier, operational.total_carbon.source],
    ['Operational', 'Total Energy', operational.total_energy.value, operational.total_energy.unit, operational.total_energy.low, operational.total_energy.high, operational.total_energy.tier, operational.total_energy.source],
    ['Operational', 'Dynamic Training', operational.training.value, operational.training.unit, operational.training.low, operational.training.high, operational.training.tier, operational.training.source],
    ['Operational', 'Inference Serving', operational.inference.value, operational.inference.unit, operational.inference.low, operational.inference.high, operational.inference.tier, operational.inference.source],
    ['Full Lifecycle', 'Total Carbon', fullLifecycle.total_carbon.value, fullLifecycle.total_carbon.unit, fullLifecycle.total_carbon.low, fullLifecycle.total_carbon.high, fullLifecycle.total_carbon.tier, fullLifecycle.total_carbon.source],
    ['Full Lifecycle', 'Total Energy', fullLifecycle.total_energy.value, fullLifecycle.total_energy.unit, fullLifecycle.total_energy.low, fullLifecycle.total_energy.high, fullLifecycle.total_energy.tier, fullLifecycle.total_energy.source],
    ['Full Lifecycle', 'Embodied Hardware', fullLifecycle.embodied_hardware.value, fullLifecycle.embodied_hardware.unit, fullLifecycle.embodied_hardware.low, fullLifecycle.embodied_hardware.high, fullLifecycle.embodied_hardware.tier, fullLifecycle.embodied_hardware.source],
    ['Full Lifecycle', 'Periodic Retraining', fullLifecycle.retraining.value, fullLifecycle.retraining.unit, fullLifecycle.retraining.low, fullLifecycle.retraining.high, fullLifecycle.retraining.tier, fullLifecycle.retraining.source],
  ];

  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  downloadFile(csv, 'lifecycle_ledger_audit.csv', 'text/csv');
}
