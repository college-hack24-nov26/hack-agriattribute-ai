# HACK CORE 2026 - Ideation Phase Concept Note

## 1. Project Overview
**Team Number:** 15
**Team Lead:** Soham Prabhakar Kadu
**Team Members:** Singireddy Prabhumitrareddy, Bhakti Ajay Kadam
**Problem Statement:** 07 - Yield Attribution & ROI Predictor
**Primary Mentors:** Dr. Shahbaz (ANNAM.AI), Hana Hafer (Syngenta)

---

## 2. Problem Statement & Motivation
Farmers face a critical challenge termed by Syngenta as "Seeing is Believing". When a farmer applies a biological product (like a biostimulant) and observes a high yield at harvest, it is difficult to determine whether the success was due to the biological product itself, or simply a result of favorable confounding factors such as excellent monsoon rains, superior soil organic carbon, or ideal temperatures. Without clear, data-driven attribution, farmers hesitate to reinvest in biologicals.

Our objective is to build a robust, AI-driven platform that estimates the yield lift and financial ROI of a biological input, stripping away the "noise" of weather and soil variability.

---

## 3. Proposed Solution: AgriAttribute AI
AgriAttribute AI is an end-to-end Machine Learning pipeline and interactive farmer-facing dashboard that mathematically decomposes crop yield into its core drivers.

### 3.1 Key Innovations
1. **Farmer-First UX (Empathetic Design):** We abstracted complex agronomic variables (GDD, SOC, NDVI) into intuitive toggles (e.g., "Soil Quality", "Monsoon Rain", "Heat Waves"). This ensures the tool is accessible to non-technical farmers while retaining a hidden "Agronomist Mode" for experts.
2. **Multi-Lingual Hyper-Localization:** The platform natively supports English, Hindi, Marathi, and Telugu, critical for penetrating the diverse Indian agricultural landscape across regions like Vidarbha and Telangana.
3. **Counterfactual SHAP Attribution:** Using a Random Forest regressor (benchmarked against XGBoost) combined with SHAP (SHapley Additive exPlanations), our model creates a "Digital Twin" of the farm. It simulates the yield *without* the biological product and compares it against the yield *with* the product, definitively isolating the biological efficacy.
4. **Actionable Outputs:** 
   - Generates a branded, downloadable A4 PDF Report detailing the 10-day weather forecast (via Meteoblue) and financial ROI.
   - Includes a 1-click WhatsApp integration to share a pre-framed, localized ROI summary directly to farmers' phones.

---

## 4. Technical Feasibility & Architecture
The solution is fully implemented as a working prototype using Python and Streamlit.

### 4.1 Data & API Integrations
- **Meteoblue Weather API:** Integrated to pull historical growing degree days (GDD), cumulative rainfall, heat stress telemetry, and 10-day agronomic forecasts.
- **Syngenta CE Hub API:** Integrated to pull localized product recommendations and optimal dosage parameters (L/ha) for specific crop targets.
- **ISRIC SoilGrids:** Utilized to establish baseline Soil Organic Carbon (SOC) and pH profiles across 5 major Indian agro-climatic zones.

### 4.2 Machine Learning Pipeline
- **Algorithm:** Random Forest regression (XGBoost benchmarked within 0.0001 R2). Chosen for its ability to handle non-linear interactions between weather (heat stress) and biology (biostimulant buffering).
- **Explainability:** SHAP values are extracted dynamically in the Streamlit UI to render a donut chart, visually proving to the farmer exactly what percentage of their yield came from the biological input versus the weather.

---

## 5. Expected Impact
By deploying AgriAttribute AI, Syngenta can:
1. **Increase Sales Conversion:** Armed with PDF reports and WhatsApp summaries proving an exact 300%+ ROI, sales representatives can confidently close deals.
2. **Build Trust:** By openly acknowledging when weather played a major role (and mathematically isolating it), Syngenta builds long-term trust with farmers through radical transparency.
3. **Scale Education:** The multilingual UI ensures that the complex science of biostimulant efficacy is democratized across rural India.

**"Seeing is Believing. AgriAttribute AI makes the invisible, visible."**
