# Audit response (November 2026)

Each issue raised in the technical audit, what changed, and where to check it. Status: **Fixed**, **Partly fixed**,
**Open** (known limit, stated in the app).

## P0 — scientific credibility

| # | Issue | Status | What changed | Check |
|---|---|---|---|---|
| 1.1 | Simulated data labelled as ICAR / company trials | **Fixed** | `data/field_trials.csv` `source` now says *SIMULATED … not real field trials*; the fake ICAR URL and "RCBD - 4 replications" are gone; the generator writes the same labels. The app, README and model card call it simulated everywhere. | `data/field_trials.csv`, `pipeline/offline_training_pipeline.py` |
| 1.1 | Need real field data | **Open** | Cannot be fixed in code. The Season Journal stores real treated/untreated outcomes so the model can be re-trained. | README "Known limits" |
| 1.2 | Pooled R² hides poor within-crop accuracy | **Fixed** | `pipeline/evaluate_model.py` reports per-crop R², MAE, RMSE and error % on the held-out 2025 season (within-crop R² −0.27 to 0.69). The YIELD tab model card shows these instead of a "PRODUCTION VALIDATED" badge. | `models/per_crop_metrics.json`, `services/model_card_ui.py` |
| 1.2 | Evaluate the treatment effect separately | **Fixed** | Same script compares the model's with/without lift with the observed lift on held-out paired plots, overall and per crop. | `treatment_effect` in `models/per_crop_metrics.json` |
| 1.3 | SHAP presented as causal attribution | **Fixed** | Wording changed in the app, simulator docstrings and README: SHAP = why the model predicts this; counterfactual lift = model estimate of the effect; causal proof = needs real paired/randomised trials (stated, not claimed). The fake 65 % soil / 35 % weather split was removed. | YIELD tab, `services/decision_simulator.py` |
| 2 | Dose extrapolation (soybean 11.5 → 113 q/acre at 3 L) | **Fixed** | Trials used one dose per crop, so the model is always queried at that dose; the farmer's dose scales the credited lift (linear up to the trial dose, flat above) and the cost. | `tests/test_scenarios.py::test_soybean_stays_in_a_plausible_range`, `::test_overdosing_never_raises_yield` |
| 2 | Unit mismatch (kg/ha vs q/acre, L/ha vs L/acre) | **Fixed** | All money is ₹/acre; fertiliser kg/ha is converted (÷ 2.4711) in one function; dose is L/acre for cost. | `services/economics.py`, `tests/test_economics.py` |
| 2 | Fixed ₹1,200 biological cost | **Fixed** | Cost = dose × product price per litre + application labour, per crop. | `economics.treatment_cost_per_acre` |
| 2 | Rainfall 780 mm and GDD 2,350 for every crop; NDVI 0.76 | **Fixed** | Season normals per crop from the training data (`models/season_normals.json`), labelled "season normal, not a live reading". Live temperature is clipped to the trained range. | `economics.season_inputs` |
| 2 | One pooled error band for every crop | **Fixed** | Band = held-out MAE of the selected crop. "Calibrated 90 % band" wording removed. | `economics.crop_error` |
| 2 | ROI not independently testable | **Fixed** | One formula in `services/economics.py`; the simulator, Today card and PDF use it. Negative lift shows as a loss; ROI is undefined (not 999 %) without cost; hidden ×1.03 / ×1.04 multipliers removed. | 16 unit tests (`pytest -q`) |
| 2 | Quality premium inflating ROI | **Fixed** | ROI uses the plain mandi price; the assumed +3.5 % premium is shown but not added. | `app.py` crop price |

## P1 — production reliability

| # | Issue | Status | What changed |
|---|---|---|---|
| 3 | Source registry | **Fixed** | 17 sources with owner, link, retrieval, update frequency, coverage, integration method and validation status (Today → *Full source registry*). |
| 3 | MSP 2026-27 in data vs 2024-25 in the pricing engine | **Fixed** | Pricing uses MSP 2026-27 from the bundled report wherever it lists the crop and says which year it used. |
| 3 | Sentinel-2 NDVI fixed at 0.76 | **Partly fixed** | Replaced by a labelled season normal; the provenance registry says "no satellite feed connected". Real Sentinel-2 is still open. |
| 3 | Snapshot data called live | **Fixed** | Mandi data is labelled "bundled snapshot, not a live feed"; the trust strip counts it as simulated/snapshot. |
| 4 | Geolocation over HTTP | **Fixed** | The `http://ip-api.com` fallback is replaced by HTTPS. IP lookup runs only when GPS is unavailable. |
| 4 | Gemini 429 → offline fallback | **Fixed** | One shared caller tries `gemini-2.5-flash`, then lite models; per-minute limits pause ~30 s, per-day limits park that model. Used by the assistant, photo check and translation. |
| 4 | IndicTrans2 gated model → HTTP 403 | **Fixed** | Not attempted unless `HF_TOKEN` or `INDICTRANS_MODEL_DIR` is set; torch/transformers moved to `requirements-optional.txt`. |
| 4 | Languages partly English | **Partly fixed** | Whole-app translation layer with pre-seeded caches for 8 languages in `data/i18n/` (~2,500 strings each); markdown headings and lists are now translated (they were skipped); every translation must be in the target script (small models sometimes answered in Hindi for Telugu or Gujarati; 2,000 such entries were purged and redone); navbar labels are hand-written. Measured: 86–88 % of visible words in the target script (the rest is product names, units, file names). Machine translation still needs a native-speaker review. |
| — | App feels laggy | **Fixed** | Lazy tabs (only the open tab runs), sticky widget state, stale-while-revalidate cloud reads, background prefetch, deferred downloads, fragments. Tab switch < 1 s, same-tab rerun ~0.2 s (was ~3 s; first load 7 s, was 24–59 s). |

## P2 — product maturity

| # | Issue | Status | What changed |
|---|---|---|---|
| 4 | LeafVision fixed "confidence" from metadata rules | **Partly fixed** | Now called a *rule score (not a probability)*; engine named "rule-based colour & lesion analyser"; fake latency floor removed. A trained classifier is still open. |
| 4 | MobileNetV3 loaded but unused | **Fixed** | The unused torch backbone is not imported; torch is optional. |
| 5 | Company needs / waste buyers not genuine | **Stated** | All samples are fictional and marked DEMO; real companies can post through the portal. No real brand names are used for fake demands. |
| 5 | Plant Smart uses simulated plans | **Open** | Not in this build. |
| 5 | River Watch sensor validation | **Open** | Simulator or uploaded CSV only; thresholds match the firmware; the float is not built. |
| — | Automated CI | **Fixed** | `.github/workflows/tests.yml` runs lint, the unit tests and the model report on every push. |

## Test counts (reconciled)

* `pytest -q`: **16** tests (8 economics, 8 scenario simulator incl. 4 parametrised crops).
* Click-through (Streamlit AppTest): every one of the 13 tabs opened, every keyed button clicked and every selectbox
  cycled: **248 interactions, 0 failures** on the final build (median 0.45 s, p90 0.86 s per interaction). Language
  runs in Marathi, Telugu and Punjabi: 13/13 tabs, 0 exceptions. Switching to Marathi in a real browser: 0.5 s.
* The earlier "34 unit tests / 16 click-through checks" figures came from a different copy of the project and are
  superseded by these.
Neither proves agronomic validity; that needs real field data.
