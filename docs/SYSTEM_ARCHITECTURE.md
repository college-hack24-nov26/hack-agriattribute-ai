> **Note (Nov 2026):** written for Hack Core 2026. Where it differs from [`README.md`](../README.md) or [`AUDIT_RESPONSE.md`](AUDIT_RESPONSE.md), those are current: the training data is simulated, accuracy is reported per crop, and SHAP explains the model rather than proving cause.

# AgriAttribute — System Architecture & Technical Design

**Hack Core 2026 — Problem Statement 07 (Syngenta Biologicals & ANNAM.AI)**  
*Team 15: Soham Prabhakar Kadu, Singireddy Prabhumitrareddy, Bhakti Ajay Kadam*

---

## 1. Overview & Core Engineering Objectives

The core goal of AgriAttribute is to answer a fundamental agricultural attribution question: **How much of a crop's yield boost was caused by biological treatment, and how much was simply the result of good rainfall, soil nutrients, or regional baselines?**

To solve this in a production-ready web application without requiring heavy cloud infrastructure, we designed the platform with four technical principles:

1. **Lightweight Edge Inference:** The leaf vision pathology scanner runs locally on the CPU in under 30 ms using quantized PyTorch models, avoiding cloud GPU hosting costs and working on low-bandwidth field connections.
2. **Resilient External Integrations:** Weather data uses an automated 3-key rotation mechanism over OpenWeatherMap to handle rate limits and 429 errors seamlessly.
3. **Explainability over Black-Box Output:** Rather than just predicting a final yield number, we use SHAP (SHapley Additive exPlanations) to show how the model splits its prediction between the biological product, weather and soil, and a with/without counterfactual to estimate the lift. Both are model estimates, not causal proof.
4. **Touch-First Accessibility:** The UI is full-width, touch-friendly, supports 4 Indian languages (English, Hindi, Marathi, Telugu), and includes an adaptive font-scaling mode for outdoor sunlight visibility.

---

## 2. System Flow

The application coordinates data from field sensors, public government APIs, and trained models:

```text
[ Farmer / Extension Worker ]
       │
       ├── Selects Crop, Region, & Biological Dosage
       ├── (Optional) Uploads Leaf Photo or Speaks via Mic
       │
       ▼
[ Streamlit Web Interface (app.py) ]
       │
       ├── 1. Weather Telemetry (openweather_service.py)
       │      └─ Fetches local temp, humidity, wind & 5-day forecast (with 3-key failover)
       │
       ├── 2. Market Economics (agmarknet_engine.py)
       │      └─ Compares bundled APMC modal prices with MSP 2026-27
       │
       ├── 3. Soil Health Card (pricing_and_soil_engine.py)
       │      └─ Evaluates 12 soil parameters & calculates bag-level N-P-K requirements
       │
       ├── 4. Leaf Pathology (leafvision_engine.py)
       │      └─ On-device lesion segmentation, severity rating, and dual prescription
       │
       ├── 5. Yield & Attribution Engine (models/model.pkl & models/shap_explainer.pkl)
       │      └─ The Random Forest model predicts total yield; SHAP isolates biological lift (ΔY)
       │
       ├── 6. Multimodal Assistant (gemini_service.py)
       │      └─ Google Gemini 2.5 Flash handles voice notes, photos, and localized Q&A
       │
       ▼
[ Persistence & Export Layer ]
       ├── Supabase Cloud PostgreSQL (Farm Memory ledger)
       ├── Downloadable A4 PDF Advisory (pdf_report.py)
       ├── Multi-Sheet Excel Workbook (supabase_client.py)
       └── 1-Click WhatsApp ROI Sharing
```

---

## 3. The Attribution Pipeline (model-based, not causal proof)

### The Problem with Simple Linear Comparisons
In agriculture, biological yield response is highly non-linear. Under mild heat stress, a biostimulant like Syngenta Quantis protects stomatal conductance and prevents flower drop, resulting in a noticeable yield increase. However, if monsoon rains are optimal and temperatures remain mild, the baseline yield is already high, and the relative boost is smaller. A simple linear regression fails to capture these climate-product interaction effects.

### Our Solution: Tree-ensemble model + SHAP TreeExplainer
1. **Model Architecture:** We trained an `XGBRegressor` on 1,200 domain-calibrated Indian field trial data points across 12 major crops (Soybean, Cotton, Rice, Wheat, Sugarcane, Maize, Groundnut, Mustard, Gram, Tur, Onion, Tomato).
2. **Feature Space:** Features include 12 soil test parameters (N, P, K, OC, pH, EC, S, Ca, Mg, Zn, Fe, Cu, Mn, B), environmental variables (cumulative rainfall, growing degree days, heat stress days above 38°C, peak satellite NDVI), crop type, region, and biological treatment (flag and dosage in L/ha).
3. **Attribution Decomposition:**
   Using the additive property of Shapley values:
   $$\text{Yield} = \phi_0 + \phi_{\text{bio}} + \phi_{\text{weather}} + \phi_{\text{soil}} + \phi_{\text{crop/region}}$$
   Where:
   - $\phi_{\text{bio}}$ is the model's attribution to the biological product (not a causal estimate) ($\Delta Y$).
   - $\phi_{\text{weather}}$ captures the net effect of rainfall and thermal stress.
   - $\phi_{\text{soil}}$ captures organic carbon, nutrient deficits, and pH buffering.
   - $\phi_0$ is the regional expected baseline.
4. **Validation Performance:**
   - **$R^2$ Score:** pooled `0.9944` on simulated data (misleading alone; within-crop −0.27 to 0.69, see `models/per_crop_metrics.json`)
   - **Mean Absolute Error (MAE):** `2.78 q/acre`
   - **Root Mean Squared Error (RMSE):** `6.82 q/acre`

---

## 4. Subsystem Details

### A. Resilient Weather Telemetry (`openweather_service.py`)
- Coordinates 3 independent API keys in a failover pool (`current weather`, `maps`, `google map`).
- If an active key returns HTTP 429 (rate limited) or times out, the service automatically switches to the next key and logs the failover without crashing the user session.
- Calculates wind shear spray windows: $< 15\text{ km/h}$ is flagged as optimal for spraying, while $> 25\text{ km/h}$ warns the user of droplet drift.

### B. On-Device Plant Pathology (`leafvision_engine.py`)
- Uses a lightweight vision model fine-tuned on crop pathology samples.
- Extracts 24 biometric parameters from the uploaded image, including green canopy ratio, lesion surface percentage, necrosis index, and chlorosis ratio.
- Runs entirely on CPU in $20-45\text{ ms}$, removing the need for a persistent cloud GPU.
- Returns a dual recommendation: approved CIBRC chemical controls alongside biological alternatives (*Trichoderma viride*, *Pseudomonas fluorescens*, Neem oil).

### C. Mandi Intelligence & MSP Tracker (`agmarknet_engine.py`)
- Ingests daily modal wholesale spot prices from Indian APMCs.
- Benchmarks prices against MSP 2026-27 (bundled report).
- Calculates 72-hour price momentum:
  $$\text{Price Delta \%} = \frac{\text{Spot Price} - \text{MSP}}{\text{MSP}} \times 100$$
  If trading below MSP, the app recommends utilizing central procurement centers or negotiable warehouse receipts (NWR).

### D. Soil Health Card Integration (`pricing_and_soil_engine.py`)
- Implements the Indian Government's DAC&FW Soil Health Card response equations.
- Evaluates soil nutrient deficits against target crop uptake and outputs exact bag requirements for Urea (46% N), DAP (18% N, 46% P), and MOP (60% K).
- Includes a 15% Urea reduction protocol when biological soil conditioners are applied to prevent nitrogen leaching.

### E. Cloud Farm Memory (`supabase_client.py`)
- Connects to a cloud-hosted Supabase PostgreSQL database (`wnujxbnjqrwybllvbahm.supabase.co`).
- Stores historical field journal entries, treatment dates, observed yields, and profit outcomes.
- Exports records as multi-sheet `.xlsx` workbooks and printable A4 PDF summaries.

### F. Multilingual Voice Assistant (`gemini_service.py`)
- Uses Google's Gemini 2.5 Flash API with a localized agricultural system prompt.
- Supports voice query transcription via the browser Web Speech API, text chat, and leaf image attachments.
- Available in English, Hindi, Marathi, and Telugu.

---

## 5. Model Retraining Pipeline (`retrain_pipeline.py`)

To ensure the system improves over time as real Syngenta trial data becomes available:
1. **Schema Normalization:** Uses alias mapping (`yield_q_acre` $\rightarrow$ `yield_q_per_acre`, `soc` $\rightarrow$ `soil_organic_carbon`) to ingest raw CSV trial files with inconsistent column names.
2. **Automated Fitting:** Fits the Random Forest and XGBoost regressors and keeps the better held-out score on the updated dataset and evaluates train/test splits.
3. **Explainer Recalibration:** Recomputes the TreeExplainer for the new model.
4. **Atomic Serialization:** Overwrites `models/model.pkl` and `models/shap_explainer.pkl`.

---

## 6. Official Data Sources & Citations

1. **Ministry of Agriculture & Farmers Welfare (MoA&FW):**
   - Agmarknet daily wholesale price reports: `https://agmarknet.gov.in`
   - CACP 2024–25 MSP schedules: `https://cacp.dacnet.nic.in`
2. **Department of Agriculture & Farmers Welfare (DAC&FW):**
   - Soil Health Card 12-parameter benchmarks: `https://soilhealth.dac.gov.in`
3. **India Meteorological Department (IMD):**
   - District rainfall normals: `https://mausam.imd.gov.in`
4. **ICAR-CRIDA:**
   - District Agricultural Contingency Plans: `https://crida.icar.gov.in`
5. **Scott M. Lundberg et al. (2020):**
   - *From local explanations to global understanding with explainable AI for trees*, Nature Machine Intelligence 2, 56–67.
