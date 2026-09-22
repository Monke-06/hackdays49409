# Design System & Specification Document

**Project**: Sustainable AI Lifecycle Auditor  
**Palette**: Warm Paper Editorial Palette (`#F6F5F1`, `#1B1B18`, `#1D4E6B`)  
**Status**: Milestone 1 & 2 Design Proof  

---

## 1. Architectural Philosophy

The Sustainable AI Lifecycle Auditor interface is designed as an empirical scientific instrument with a warm paper editorial aesthetic:
- **Warm Paper Canvas** (`#F6F5F1`) evokes archival scientific reports and printed journals.
- **Near-Black Charcoal Text** (`#1B1B18`) provides high contrast without harsh digital glare.
- **Deep Petroleum Accent** (`#1D4E6B`) anchors interactive elements and primary controls.
- **Restrained Geometry**: Sharp, crisp radii (`2px` to `4px`) and light borders (`#D6D2C9`) replace bubbly UI conventions.
- **No Decorative Animations**: No count-up tickers. Numbers render immediately. Reduced-motion instantly converts transitions to 0.01ms.

---

## 2. Typography Hierarchy (Self-Hosted OFL)

Fonts are self-hosted in WOFF2 format under `frontend/public/fonts/` with real SIL Open Font License 1.1 documents.

| Role | Font Family | Weight / Style | Primary Use Case |
|---|---|---|---|
| **Editorial Headlines** | Source Serif 4 | 600 SemiBold, 400 Italic | Page titles, major section headers, methodology thesis |
| **User Interface & Forms** | IBM Plex Sans | 400 Regular, 500 Medium, 600 SemiBold | Controls, table headers, labels, descriptions, callouts |
| **Quantities & Provenance** | IBM Plex Mono | 400 Regular, 500 Medium | Numerical measurements, uncertainty bounds, code, TDP, units |

---

## 3. Color Tokens & Computed WCAG Contrast Ratios

All foreground and background color combinations were mathematically computed using the standard WCAG 2.1 relative luminance algorithm:
$$L = 0.2126 R_{\text{lin}} + 0.7152 G_{\text{lin}} + 0.0722 B_{\text{lin}}$$
$$\text{Contrast Ratio} = \frac{L_1 + 0.05}{L_2 + 0.05}$$

### Computed Contrast Ratio Table

| UI Element / State | Foreground (Hex) | Background (Hex) | Computed Ratio | WCAG 2.1 Level | Notes |
|---|---|---|---|---|---|
| **Primary Text on Warm Paper Canvas** | `#1B1B18` | `#F6F5F1` (Canvas) | **15.82 : 1** | **AAA** | Exceeds 7.0:1 |
| **Primary Text on White Surface** | `#1B1B18` | `#FFFFFF` (Surface) | **17.26 : 1** | **AAA** | Exceeds 7.0:1 |
| **Secondary Text on Warm Paper Canvas** | `#4A4944` | `#F6F5F1` (Canvas) | **8.27 : 1** | **AAA** | Exceeds 7.0:1 |
| **Secondary Text on White Surface** | `#4A4944` | `#FFFFFF` (Surface) | **9.02 : 1** | **AAA** | Exceeds 7.0:1 |
| **Muted / Helper Text on Paper Canvas** | `#6B6963` | `#F6F5F1` (Canvas) | **5.03 : 1** | **AA** | Exceeds 4.5:1 (normal text, not AAA) |
| **Muted / Helper Text on White Surface** | `#6B6963` | `#FFFFFF` (Surface) | **5.49 : 1** | **AA** | Exceeds 4.5:1 (normal text, not AAA) |
| **Muted / Helper Text on Subtle Bg** | `#6B6963` | `#EFECE6` (Subtle) | **4.66 : 1** | **AA** | Exceeds 4.5:1 (normal text, not AAA) |
| **Primary Accent Button Text** | `#FFFFFF` | `#1D4E6B` (Accent) | **8.92 : 1** | **AAA** | Exceeds 7.0:1 |
| **Accent Text/Link on Paper Canvas** | `#1D4E6B` | `#F6F5F1` (Canvas) | **8.18 : 1** | **AAA** | Exceeds 7.0:1 |
| **Accent Text/Link on White Surface** | `#1D4E6B` | `#FFFFFF` (Surface) | **8.92 : 1** | **AAA** | Exceeds 7.0:1 |
| **Danger Button Text** | `#FFFFFF` | `#8B1E1E` (Crimson) | **9.12 : 1** | **AAA** | Exceeds 7.0:1 |
| **Verdict Supported (Green)** | `#184F31` | `#EBF5EE` | **8.55 : 1** | **AAA** | Exceeds 7.0:1 |
| **Verdict Contradicted (Red)** | `#8B1E1E` | `#FAECEC` | **7.94 : 1** | **AAA** | Exceeds 7.0:1 |
| **Verdict Boundary Shift (Amber)** | `#784400` | `#FDF5E6` | **7.38 : 1** | **AAA** | Exceeds 7.0:1 |
| **Verdict Insufficient (Grey)** | `#4A4944` | `#EFECE6` | **7.65 : 1** | **AAA** | Exceeds 7.0:1 |

> [!NOTE]
> **WCAG Level Verification**: As noted, muted/helper text (`#6B6963`) achieves **AA** (5.03:1 on paper, 5.49:1 on surface, 4.66:1 on subtle background) for normal body text, not AAA. All other typography, primary controls, and status banners achieve **AAA** (≥ 7.0:1).

---

## 4. Extraction Source Markers

Extraction sources are rendered as human-readable plain text with an exact $8\times 8\text{ px}$ square indicator (no rounded badges/pills):
- **`■ Gemini (LLM Extraction)`**: Square marker `#1D4E6B` (Petroleum Blue) with text `#1B1B18`.
- **`■ Deterministic Rules Fallback`**: Square marker `#B45309` (Amber 700) with text `#1B1B18`.
- **`■ User Specified Configuration`**: Square marker `#4A4944` (Warm Grey) with text `#1B1B18`.

---

## 5. Auditing Drawer Specification

- **Purpose**: Displays the complete `LedgerAssumptions` block (grid intensity, facility PUE, GPU utilization fraction, hardware lifetime, Monte Carlo samples and seed) so users can audit the underlying assumptions.
- **Trigger**: Clicked via the dotted link `Audit Stated Assumptions (1000 MC Runs)` in the results header, or triggered programmatically.
- **Origin**: The backend schema in `schemas.py` specifies: *"The UI shows this block alongside any result so the user can audit it."* The slide-out drawer was implemented to keep the primary footprint display clean while allowing full inspection. If preferred, this block can be rendered directly inline as a collapsible card alongside the result.
- **Animation & Timing**:
  - Backdrop fade-in: `opacity: 0` to `1` over `200ms` with `cubic-bezier(0.16, 1, 0.3, 1)`.
  - Panel slide-in: `transform: translateX(100%)` to `0` over `200ms` with `cubic-bezier(0.16, 1, 0.3, 1)`.
  - Reduced-motion fallback: `0.01ms` (instant toggle with no motion).
