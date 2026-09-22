# Frontend Architectural & Compliance Audit

**Application**: Sustainable AI Lifecycle Auditor  
**Audit Date**: September 2026  
**Auditor**: Antigravity Frontend Pair Programmer  
**Compliance Standard**: WCAG 2.1 (AAA / AA), SIL OFL 1.1, Zero-Invented-Numbers Invariant  

---

## 1. Design Tokens & Styling Architecture

- **No Tailwind CSS**: Built exclusively with semantic CSS custom properties in [`frontend/src/styles/tokens.css`](file:///c:/hackdays/frontend/src/styles/tokens.css) and scoped CSS Modules (`*.module.css`).
- **Warm Paper Editorial Palette**:
  - Background Canvas: `#F6F5F1`
  - Elevated Surfaces: `#FFFFFF`
  - Subtle Neutral: `#EFECE6`
  - Primary Text: `#1B1B18` (Near-black charcoal)
  - Secondary Text: `#4A4944`
  - Muted/Helper Text: `#6B6963`
  - Accent Interactive: `#1D4E6B` (Deep petroleum blue)
  - Verdict Banners: `#184F31` (Green), `#8B1E1E` (Red), `#784400` (Amber), `#4A4944` (Grey).

### WCAG 2.1 Contrast Verification (Script Computed)
All pairs were mathematically verified via [`frontend/scripts/verify_contrast.py`](file:///c:/hackdays/frontend/scripts/verify_contrast.py) using WCAG 2.1 relative luminance:

| UI Pairing | Foreground | Background | Ratio | Conformance |
|---|---|---|---|---|
| Primary text on paper canvas | `#1B1B18` | `#F6F5F1` | 15.82 : 1 | **AAA** |
| Primary text on white surface | `#1B1B18` | `#FFFFFF` | 17.26 : 1 | **AAA** |
| Secondary text on paper canvas | `#4A4944` | `#F6F5F1` | 8.27 : 1 | **AAA** |
| Secondary text on white surface | `#4A4944` | `#FFFFFF` | 9.02 : 1 | **AAA** |
| Muted/helper text on paper canvas | `#6B6963` | `#F6F5F1` | 5.03 : 1 | **AA** (normal text) |
| Muted/helper text on white surface | `#6B6963` | `#FFFFFF` | 5.49 : 1 | **AA** (normal text) |
| Muted text on subtle background | `#6B6963` | `#EFECE6` | 4.66 : 1 | **AA** (normal text) |
| Primary action button | `#FFFFFF` | `#1D4E6B` | 8.92 : 1 | **AAA** |
| Danger action button | `#FFFFFF` | `#8B1E1E` | 9.12 : 1 | **AAA** |
| Supported Verdict Banner | `#184F31` | `#EBF5EE` | 8.55 : 1 | **AAA** |
| Contradicted Verdict Banner | `#8B1E1E` | `#FAECEC` | 7.94 : 1 | **AAA** |
| Boundary Shift Verdict Banner | `#784400` | `#FDF5E6` | 7.38 : 1 | **AAA** |
| Insufficient Evidence Banner | `#4A4944` | `#EFECE6` | 7.65 : 1 | **AAA** |

---

## 2. Typography & Font Licensing

All fonts are self-hosted in WOFF2 format under [`frontend/public/fonts/`](file:///c:/hackdays/frontend/public/fonts/):
- **Source Serif 4**: Regular, SemiBold, Bold, Italic (SIL OFL 1.1)
- **IBM Plex Sans**: Regular, Medium, SemiBold, Bold, Italic (SIL OFL 1.1)
- **IBM Plex Mono**: Regular, Medium, SemiBold, Italic (SIL OFL 1.1)

Each font directory contains its official, unmodified `OFL.txt` / `LICENSE.txt` file confirming open redistribution rights and complete absence of external network font requests.

---

## 3. Motion & Reduced-Motion Enforcement

All animations follow the strict functional motion table:
- **Button / Input focus**: `100ms var(--motion-ease-default)`
- **Modal / Callout Banners**: `180ms var(--motion-ease-default)`
- **Scatter Plot Hover & Transitions**: `150ms var(--motion-ease-default)`
- **Drawer Slide**: `200ms var(--motion-ease-default)`
- **Zero Decorative Count-Ups**: Numerical counters and tickers are prohibited; quantities render immediately.
- **Accessibility**: `@media (prefers-reduced-motion: reduce)` globally sets `animation-duration: 0.01ms !important` and `transition-duration: 0.01ms !important`.

---

## 4. Zero Invented Numbers Invariant

- **Strict Schema Adherence**: Every numerical quantity is rendered via [`QuantityDisplay`](file:///c:/hackdays/frontend/src/components/base/QuantityDisplay.tsx) using the `Quantity` object returned directly by the backend API:
  - `value`: Point estimate
  - `[low, high]`: 5th-to-95th percentile uncertainty range
  - `tier`: `"measured"` or `"modeled"` displayed as a human-readable tag
  - `source`: Empirical citation (Ember, Boavizta, Green Algorithms)
- **Binding Constraint Rule**: When no architecture candidate qualifies under the user's SLA constraint, `/api/v1/recommend` returns `winner_operational: null` and `winner_full_lifecycle: null`. The UI strictly displays the `binding_constraint` message and suppresses any recommendation.

---

## 5. Screen & Feature Coverage

1. **Lifecycle Ledger (`/`)**:
   - Preset quick-fill scenarios from `/api/v1/meta`.
   - Dual-boundary toggle: Operational Boundary vs Full Lifecycle Boundary.
   - Comprehensive component breakdown (training, inference, embodied hardware, retraining, storage, networking).
   - Off-canvas or inline auditing inspector for stated assumptions.
   - Client-side JSON and CSV data export.
2. **Architecture Recommender (`/recommender`)**:
   - Workload constraint configuration and multi-candidate evaluation.
   - Interactive Pareto Frontier scatter chart (Operational Carbon vs P95 Latency).
   - Life-Cycle Break-Even Sensitivity Explorer with daily request volume slider.
   - Dual-boundary winner cards with boundary reversal alerts.
3. **Claim Auditor & Verifier (`/claims`)**:
   - Natural language claim extraction via `/api/v1/claims/extract`.
   - Extraction source plain text with an exact $8\times 8\text{ px}$ square indicator (`■ Gemini`, `■ Rules Fallback`, `■ User Specified`).
   - Deterministic 3-tier cascade verifier via `/api/v1/claims/check`.
4. **Methodology Documentation (`/methodology`)**:
   - Mathematical derivation of paired Monte Carlo cancellation (`checker.py` and `uncertainty.py`).
5. **Not Available States (`/inventory-parse`, `/self-footprint`)**:
   - Dedicated explanatory views for unbuilt backend endpoints.
6. **Privacy & Terms (`/privacy`, `/terms`)**:
   - Full disclosure on local computation, zero-tracking, and scientific disclaimers.
7. **Design Specimen (`/design`)**:
   - Dev-only visual test harness using non-data placeholder text.
