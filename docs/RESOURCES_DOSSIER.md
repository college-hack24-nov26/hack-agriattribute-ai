> **Note (Nov 2026):** written for Hack Core 2026. Where it differs from [`README.md`](../README.md) or [`AUDIT_RESPONSE.md`](AUDIT_RESPONSE.md), those are current: the training data is simulated, accuracy is reported per crop, and SHAP explains the model rather than proving cause.

# AgriAttribute — Complete Data Sources & Technology Catalog

**Hack Core 2026 — Problem Statement 07 (Syngenta Biologicals & ANNAM.AI)**  
*Team 15: Soham Prabhakar Kadu, Singireddy Prabhumitrareddy, Bhakti Ajay Kadam*  

---

## 1. Official Indian Government Portals & Agricultural Registries

Every agricultural baseline, statutory price floor, and soil threshold in this project is anchored in official Indian Government publications and agricultural research bodies:

| Resource Name | Statutory Authority / Ministry | Official Portal | What We Used from this Source |
| :--- | :--- | :--- | :--- |
| **Agmarknet Portal** | Directorate of Marketing & Inspection (DMI), Ministry of Agriculture & Farmers Welfare (MoA&FW) | `https://agmarknet.gov.in` | Live daily modal wholesale spot prices (₹/Quintal), 3-day arrival volumes (MT), and 72-hour price momentum for 24 agricultural commodities across Indian APMCs. |
| **CACP Minimum Support Price (MSP)** | Commission for Agricultural Costs & Prices (CACP), MoA&FW | `https://cacp.dacnet.nic.in` | Statutory floor prices (MSP 2026-27 from the bundled Agmarknet report; CACP 2024–25 table as fallback) formulated on the $A2+FL \times 1.5$ cost-of-cultivation standard to benchmark market discounts and premiums. |
| **Soil Health Card (SHC) Scheme** | Department of Agriculture & Farmers Welfare (DAC&FW) | `https://soilhealth.dac.gov.in` | Official 12-parameter soil fertility benchmarks (N, P, K, S, Ca, Mg, Zn, Fe, Cu, Mn, B, OC, pH, EC) across 5 Indian agro-climatic zones for bag-level fertilizer calculations. |
| **IMD Mausam Agro-Met Services** | India Meteorological Department, Ministry of Earth Sciences (MoES) | `https://mausam.imd.gov.in` | District-level cumulative monsoon rainfall normals, growing degree days (GDD), and extreme heat degree days for physiological stress indexing. |
| **ICAR-CRIDA Agricultural Contingency Plans** | Central Research Institute for Dryland Agriculture (ICAR) | `https://crida.icar.gov.in` | District Agricultural Contingency Plans (DACP) classifying Vidarbha & Deccan Plateau Vertisols as the national Soybean–Cotton agro-ecological corridor. |
| **Government of Maharashtra Kharif Census** | Commissioner of Agriculture, Govt. of Maharashtra | `https://krishi.maharashtra.gov.in` | Official Weekly Kharif Sowing Reports establishing regional cultivation acreage shares (Soybean 42%, Cotton 36%, Paddy 12%, Sugarcane 10%). |
| **CIBRC Statutory Pesticide Registry** | Central Insecticides Board & Registration Committee, MoA&FW | `https://cibrc.nic.in` | Approved active ingredients, dosage rates (g/L), safety pre-harvest intervals (PHI), and chemical vs. biocontrol prescriptions. |

---

## 2. Machine Learning, Explainable AI & Computer Vision

All algorithmic decisions run locally on standard hardware without relying on opaque third-party black boxes:

| Technology / Model | Scientific Citation / Architecture | Code / Artifact Location | Performance & Role in Application |
| :--- | :--- | :--- | :--- |
| **Random Forest (deployed); XGBoost benchmarked** | Breiman (*Machine Learning*, 2001); Chen & Guestrin (*KDD 2016*) | `models/model.pkl` | Pooled $R^2 = 0.994$ on the 2025 held-out season of **simulated** data, misleading on its own: within-crop $R^2$ is −0.27 to 0.69 and the typical error 3–13 % of each crop's mean (`models/per_crop_metrics.json`)<br>Trained across 36 agricultural features capturing non-linear yield responses under climate and biological interactions. |
| **SHAP TreeExplainer** | Scott M. Lundberg et al. (*Nature Machine Intelligence*, 2020) | `models/shap_explainer.pkl` | Exact cooperative game-theoretic feature attribution ($f(x) = \phi_0 + \sum \phi_i$) isolating biological input lift ($\Delta Y$) from rainfall and soil noise. |
| **Google Gemini 2.5 Flash** | Google DeepMind (2025) | `gemini_service.py` | Multimodal conversational reasoning engine with context-aware prompt orchestration, live agricultural parameter ingestion, and multilingual dialogue. |
| **LABA-SNU LeafVision 2.0** | Lightweight Vision Foundation Model | `leafvision_engine.py` | In-browser foliar disease diagnosis running in **$24.5\text{ ms}$ on edge CPU** with 24-parameter biometric feature extraction and lesion segmentation. |
| **Thermal Stress Index (TSI)** | Agro-meteorological physiological heat formula | `app.py` | $\text{TSI} = T_{\text{ambient}} + 0.55 (1 - \frac{\text{RH}}{100})(T_{\text{ambient}} - 14.5)$ triggering heat-stress biostimulant alerts when $> 32^\circ\text{C}$. |
| **Automated Model Retrainer** | Smart Column Synonym Alias Resolver | `retrain_pipeline.py` | Automated schema normalizer enabling field researchers to drag-and-drop CSV trial datasets for instant on-the-fly model recalibration. |

---

## 3. Cloud Infrastructure & External APIs

| Service / Infrastructure | Provider / Endpoint | Implementation Notes | Role in System Architecture |
| :--- | :--- | :--- | :--- |
| **OpenWeatherMap 3-Key Failover Engine** | OpenWeatherMap REST API (`api.openweathermap.org`) | `openweather_service.py` | Real-time weather telemetry (Temp, RH%, Wind, Pressure) and 5-day predictive agro-meteorological forecast with automatic API key rotation. |
| **Supabase Cloud PostgreSQL** | Supabase Cloud Database (`wnujxbnjqrwybllvbahm.supabase.co`) | `supabase_client.py` | Persistent cloud ledger for the **Farm Memory** audit trail, logging all farmer decisions, diagnoses, and harvest metrics. |
| **ISRIC SoilGrids 250m** | International Soil Reference & Information Centre (`soilgrids.org`) | Public Global REST API | Gridded spatial soil covariates including depth-to-bedrock, bulk density, and baseline soil organic carbon (SOC g/kg). |
| **Sentinel-2 Earth Observation** | European Space Agency (ESA Copernicus) | Open-Access Data | **Not integrated yet**: NDVI uses a per-crop season normal until Sentinel-2 is connected. |

---

## 4. Biological Inputs & Crop Protection Formulations

| Product / Formulation | Manufacturer / Source | Active Ingredients | Mode of Action & Practical Use Case |
| :--- | :--- | :--- | :--- |
| **Syngenta Quantis** | Syngenta Biologicals | Organic carbon (15%), amino acids, peptides, potassium | Activates molecular chaperone proteins to protect stomatal conductance during heat waves (> 35°C) and moisture stress. |
| **Syngenta Isabion** | Syngenta Biologicals | Free amino acids (62.5%), short & long-chain peptides | Enhances root nutrient uptake, stimulates vegetative chlorophyll synthesis, and accelerates recovery from chemical phytotoxicity. |
| **Trichoderma viride** | CIBRC Approved Bio-fungicide | Fungal biocontrol strain ($2 \times 10^6\text{ cfu/g}$) | Antagonistic biological remediation for soil-borne root rot, collar rot, and damping-off disease complexes. |
| **Pseudomonas fluorescens** | CIBRC Approved Bio-agent | Siderophore-producing rhizobacteria ($1 \times 10^8\text{ cfu/g}$) | Induces systemic resistance against foliar blast, blight, and fungal pathogens while mobilizing bound soil phosphorus. |

---

## 5. Python Libraries & Dependencies

All libraries pinned in `requirements.txt` for reliable local reproduction:

| Python Package | Version Spec | Functional Role in Architecture |
| :--- | :--- | :--- |
| `streamlit` | $\ge 1.30.0$ | Full-width reactive web UI, touch-friendly components, session caching, and device view state management. |
| `xgboost` | $\ge 2.0.0$ | High-performance gradient boosted decision tree regression for non-linear yield prediction. |
| `shap` | $\ge 0.44.0$ | Cooperative game-theoretic TreeExplainer for additive attribution and donut visualization. |
| `plotly` | $\ge 5.18.0$ | High-definition interactive charts (120-day growth trajectory divergence curves, attribution breakdowns). |
| `pandas` | $\ge 2.0.0$ | Dataframe manipulation, time-series aggregation, and automated CSV synonym schema normalization. |
| `numpy` | $\ge 1.24.0$ | Vectorized mathematical operations, polynomial growth curve modeling, and matrix computations. |
| `scikit-learn` | $\ge 1.3.0$ | Dataset partitioning, cross-validation, and statistical metric evaluations ($R^2$, RMSE, MAE). |
| `joblib` | $\ge 1.3.0$ | Efficient disk serialization and deserialization of machine learning models and explainer artifacts. |
| `requests` | $\ge 2.31.0$ | Resilient HTTP networking with timeouts and failover logic for OpenWeatherMap and Gemini REST APIs. |
| `fpdf2` | $\ge 2.7.5$ | Programmatic PDF rendering engine compiling Unicode-sanitized A4 advisory reports for bank/KVK submissions. |
| `openpyxl` | $\ge 3.1.0$ | Multi-sheet Excel workbook export engine generating audit-ready farm financial and agronomic spreadsheets. |
| `supabase` | $\ge 2.0.0$ | Official Python client library for Supabase cloud PostgreSQL database authentication and ledger queries. |
| `Pillow (PIL)` | $\ge 10.0.0$ | Digital image processing, foliar lesion analysis, pixel intensity arrays, and HSV color space conversion. |
| `torch` & `torchvision` | $\ge 2.0.0$ | Deep learning tensor math, image normalizations, and pre-trained foundation model inference pipeline. |
| `python-dotenv` | $\ge 1.0.0$ | Secure local environment variable management isolating API secret keys from the codebase. |

---

## 6. User Interface & Accessibility Features

| Feature | Implementation | Practical Benefit for Farmers |
| :--- | :--- | :--- |
| **Adaptive Typography Engine** | Dynamic CSS Injection (`app.py`) | Three responsive view modes: `📱 Mobile Phone (Large Font)` (18.5px base, 56px touch buttons, 60px tabs), `💻 Laptop / Desktop`, and `📟 Tablet Mode` for high outdoor legibility. |
| **Native Multilingual HUD** | Custom Dictionary Module (`localization.py`) | Native translations for **English, हिन्दी, मराठी, and తెలుగు** with a clean single globe selector (`🌐`). |
| **Interactive Leaflet.js Map** | Embedded Leaflet & OpenStreetMap | Dynamic Doppler weather radar overlay, live district microclimate cards, and wind shear spray window indicators. |
| **Voice Note Query Assistant** | HTML5 / JavaScript Web Speech API | Client-side microphone recording and voice note playback for hands-free farmer queries. |
| **1-Click WhatsApp Sharing** | WhatsApp Universal URI Protocol | Formatted deep-link sharing net profit (₹/acre) and ROI % directly with local farmer groups. |

---

## 7. Problem Statement Alignment & Evaluation Checklist

| Hackathon Dimension | Syngenta & ANNAM.AI Criterion | Our Implementation & Proof Point |
| :--- | :--- | :--- |
| **Problem Formulation** | Clear framing of agronomic uncertainty | Solves farmer skepticism by mathematically isolating biological yield gain ($\Delta Y$) from monsoon weather. |
| **Data Quality & Provenance** | Grounded in authentic Indian agricultural data | Calibrated on 12 Indian crops, official 12-parameter DAC&FW Soil Health Cards, and live Agmarknet APMC mandi feeds. |
| **Explainable AI (XAI)** | Transparent, trustworthy intelligence | SHAP TreeExplainer decomposing yield into Biological vs. Weather vs. Soil vs. Baseline. |
| **Inclusive Design** | Accessibility for smallholder farmers | 4 Indian languages, voice note input, high-contrast large fonts for mobile, and zero confusing machine learning jargon. |
| **Closed-Loop Integration** | End-to-end practical workflow | Connects Sensing (weather, soil) $\rightarrow$ Decision (pricing, yield, spray window) $\rightarrow$ Action (advisory, treatments) $\rightarrow$ Record (cloud ledger) $\rightarrow$ Retraining. |
