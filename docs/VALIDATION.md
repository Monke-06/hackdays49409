# Validation Report

Schema version: 1
Generated: 2026-09-22
Test runner: pytest 9.1.1, Python 3.14.2

## Test Summary

| Suite | Tests | Passed | Failed |
|---|---|---|---|
| Schema validation | 14 | 14 | 0 |
| Green Algorithms equation | 6 | 6 | 0 |
| BLOOM training validation | 11 | 11 | 0 |
| Grid intensity (Ember) | 7 | 7 | 0 |
| Embodied carbon (Boavizta) | 5 | 5 | 0 |
| Monte Carlo uncertainty | 6 | 6 | 0 |
| SCI calculator | 4 | 4 | 0 |
| Audit (banned patterns) | 1 (manual) | 1 | 0 |
| **Total** | **57** | **57** | **0** |


## BLOOM Training Footprint Validation

Reference paper:
> Luccioni, A.S., Viguier, S., and Ligozat, A.-L. (2023).
> "Estimating the Carbon Footprint of BLOOM, a 176-Billion Parameter
> Language Model." Journal of Machine Learning Research, 24(253), 1-15.
> arXiv: https://arxiv.org/abs/2211.02001

---

### Important Methodology Clarification: Rated vs Measured Power

The energy result **reproduces the paper's published estimate, which is based on rated GPU power**, not measured energy. 

As stated in Luccioni et al. (2023), Section 4.2:
> "While we were not able to track real-time power consumption, empirical observations noted that GPU utilization was typically very high, nearing 100%."

The published energy figure of 433,196 kWh was calculated by the authors from logged GPU-hours and rated thermal design power (TDP = 400 W), not from electrical meter logs.

---

### Headline: Energy Reproduction from Hardware Specs

**Inputs:**
- Training period: March 11 to July 6, 2022 = **118 calendar days** (paper Section 3)
- Wall-clock hours: 118 × 24 = **2,832 hours**
- Hardware: **384 × NVIDIA A100 SXM4 80GB** (paper Section 3)
- GPU TDP: **400 W** (NVIDIA data sheet, cited as ref [26] in paper)
- PUE: **1.0** (dynamic GPU power only, matching Table 2 row)

```
Wall-clock energy = 2,832 h × 384 GPUs × 400 W / 1,000 = 434,995.2 kWh
```

| Metric | Computed (Spec-derived) | Published (Paper Section 4.2) | TRUE Error |
|---|---|---|---|
| Dynamic Energy (kWh) | **434,995.2** | 433,196.0 | **+0.42%** |

**Gap Analysis:**
The difference is +1,799.2 kWh (approximately 11.7 hours per GPU). This is an **unexplained gap, possibly scheduling** (the difference between calendar wall-clock time and SLURM-tracked active job time), but cannot be confirmed without the authors' raw SLURM cluster telemetry.

---

### Relabelled Test: Carbon Arithmetic Check Only

The test verifying the paper's dynamic carbon is labelled strictly as a **carbon arithmetic check**, because it feeds the paper's published energy (433,196 kWh) as an input rather than deriving energy independently:

```
433,196 kWh × 57 gCO2/kWh / 1,000 = 24,692.2 kgCO2e
Published: 24,690.0 kgCO2e
Arithmetic difference: 0.009% (minor rounding in paper)
```

With PUE = 1.2 applied to spec-derived wall-clock energy:
```
434,995.2 kWh × 1.2 × 57 gCO2/kWh / 1,000 = 29,753.7 kgCO2e
Paper Table 4 (~30 tonnes; 24,690 × 1.2 = 29,628 kgCO2e): Error = +0.42%
```

---

### Embodied Carbon: Exact Citations and Reconstruction

#### Exact Paper Text (Section 4.1 "Embodied Emissions")

> "The closest comparable computing equipment that provides LCA information is HPE’s ProLiant DL345 Gen10 Plus server, which is similar to the Apollo 6500 and has a production footprint of approximately 2500 kg of CO2eq [13]. This does not include the embodied emissions of the GPUs which are used in the server, whose embodied emissions must be calculated separately. While Nvidia does not currently disclose the carbon footprint of its GPUs, recent estimates put the lower bound of this amount at approximately 150 kg of CO2eq [9], which is the number we will use for our embodied emissions estimates."

> "Assuming a replacement rate of 6 years and 85% average usage (which are the figures provided to us by IDRIS), the figures above translate to an embodied carbon footprint of approximately 0.056 kg of CO2eq for each hour of server time and 0.003 kg of CO2eq for each hour of GPU time. Given that BLOOM training lasted a total of 1.08 million hours using, on average, 384 GPUs across 48 computing nodes, we can estimate that the embodied emissions associated to BLOOM training represent approximately 7.57 tonnes for the servers and 3.64 tonnes for the GPUs, adding a total of 11.2 tonnes of CO2eq to its carbon footprint."

#### Status of the Embodied Equation
The paper **does not present an explicit algebraic equation** (such as `E_fab = ...`). Instead, it states the assumptions provided by IDRIS (6-year replacement rate, 85% average utilization) and gives the resulting hourly rate (`~0.003 kg CO2eq / GPU-hour`). 

Reconstructing the algebraic rate from these text statements:
```
Hourly GPU rate = 150 kgCO2eq / (6 years × 8,760 h/yr × 0.85) = 0.0033575 kg/GPU-hour
Total GPU embodied = 0.0033575 × 1,082,990 GPU-hours = 3,636.1 kgCO2e (~3.64 tonnes)
```
Or expressed in calendar days:
```
Embodied = (384 × 150 / 6) × (118 / 365.25) × (1 / 0.85) = 3,648.7 kgCO2e
Paper reports: 3,640 kgCO2e (3.64 tonnes)
Difference: 0.24%
```

> [!NOTE]
> **Hardware Lifetime Scope**: The 6-year hardware lifetime is an IDRIS-specific operational assumption used strictly for this validation check. In our product engine, hardware lifetime remains fully configurable with default sources (typically 3 to 4 years for commercial datacenters).

---

### Idle Energy: Measured Facility Assumption

In Section 4.3 ("Idle Power Consumption"), the authors report on dedicated experiments at the Jean Zay cluster:
> "in Infrastructure mode (with the computing nodes turned off but the network, storage and cooling turned on), the power consumption was 27 kWh; in Idle mode (with network, storage and compute nodes on, but no processes running), the power consumption was 64 kWh. During BLOOM training, power consumption averaged at over 109 kWh. This indicates that only around 54% of the power consumption can be attributed to running the code ... whereas the remaining 46% is used for keeping the computing nodes on. Multiplying this by the total training time, this adds a further 256,646 kWh of idle power consumption on top of the dynamic power used for training BLOOM, and 14.6 tonnes of CO2eq to the overall carbon footprint of model training."

Idle power (256,646 kWh) is a facility-level physical measurement and cannot be derived from GPU specifications alone.

---

### End-to-End Lifecycle Consistency Check

> [!NOTE]
> **Methodology Boundary (Consistency Check)**: Only the dynamic energy is derived from hardware specifications (118 calendar days × 24 h × 384 GPUs × 400 W). The idle energy (256,646 kWh) is a stated facility meter measurement from Jean Zay, and the embodied hardware (11,200 kg) is a stated LCA estimate from IDRIS and HPE. This check tests the consistency of equation composition, not an independent hardware derivation of the entire cluster.

Under the paper's Table 3 accounting inputs (dynamic energy with PUE = 1.0, grid intensity = 57 gCO2/kWh, Jean Zay idle energy):

| Component | Provenance | Calculation | Carbon (kgCO2e) | Carbon (tonnes) |
|---|---|---|---|---|
| Dynamic Operational (PUE=1.0) | Derived from specs | 434,995.2 kWh × 1.0 × 57 / 1,000 | 24,794.7 | 24.79 |
| Idle Energy | Paper facility meter | 256,646.0 kWh × 57 / 1,000 | 14,628.8 | 14.63 |
| Embodied Hardware | Paper Section 4.1 LCA | 3,640 kg (GPU) + 7,570 kg (Server) | 11,200.0 | 11.20 |
| **Total Computed Lifecycle** | Sum of above | 24,794.7 + 14,628.8 + 11,200.0 | **50,623.5** | **50.62** |

**Comparison to Published Headline (Table 3 and Abstract: 50.5 tonnes):**
```
Computed Total:  50,623.5 kgCO2e (50.62 tonnes)
Published Total: 50,500.0 kgCO2e (50.50 tonnes)
Error:           +0.24% (+123.5 kgCO2e)
```
The +0.24% error directly propagates the small +0.42% scheduling gap in dynamic energy ($434,995\text{ kWh}$ vs $433,196\text{ kWh}$).

When PUE = 1.2 is factored into dynamic energy:
```
Dynamic carbon (PUE=1.2): 434,995.2 kWh × 1.2 × 57 / 1,000 = 29,753.7 kgCO2e
Total with PUE=1.2:       29,753.7 + 14,628.8 + 11,200.0 = 55,582.5 kgCO2e (55.58 tonnes)
Difference vs 50.5t:      +10.06% (reflects datacenter cooling and overhead multiplier)
```

---

## Data Sources

### Grid intensity

| Field | Value |
|---|---|
| Source | CO2.js / Ember Global Electricity Review |
| License | CC BY 4.0 |
| Fetch date | 2026-09-22 |
| Coverage | 222 countries/regions |
| Year | 2024 (some entries 2022–2023) |
| Units | gCO2eq/kWh, annual average, location-based |

### GPU embodied carbon

| Field | Value |
|---|---|
| Source | Boavizta BoaviztAPI v1 |
| License | ODbL/CC-BY-SA (datasets) |
| Fetch date | 2026-09-22 |
| Methodology | Bottom-up LCA, manufacturing phase only |
| Note | End-of-life is NOT included (Boavizta API warning) |

---

## Monte Carlo Assumptions

All ranges are labeled "under stated assumptions". Changing any single
assumption can move results outside the range.

| Parameter | Distribution | Rationale |
|---|---|---|
| GPU TDP | Uniform(TDP×0.85, TDP×1.15) | Manufacturer tolerance ±15% |
| PUE | Uniform(PUE×0.90, PUE×1.10) | Thermal and load variation |
| Grid intensity | Uniform(value×0.80, value×1.20) | Annual vs marginal/hourly spread |
| Utilization | Fixed (user-supplied) | Not randomised unless range given |
| Embodied | Uniform(Boavizta min, Boavizta max) | LCA model confidence bounds |
| Samples | 1,000 (default) | Increase to 10,000 for smoother tails |
| Seed | 42 (default) | Always recorded for reproducibility |

---

## Gemini Model Verification

**Status:** Script ready (`scripts/verify_gemini_model.py`). Live test pending `GEMINI_API_KEY`.
