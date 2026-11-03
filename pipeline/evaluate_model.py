"""
evaluate_model.py - honest evaluation of models/model.pkl.

The pooled R² in model_metrics.json (0.994) mostly measures that the model can tell a sugarcane plot
(~380 q/acre) from a mustard plot (~8 q/acre). This script reports what a farmer actually needs:

  1. Per-crop accuracy on the held-out 2025 season (R², MAE, RMSE, MAE as % of the crop's mean yield).
  2. Treatment-effect recovery. The training data is simulated, so the true biological lift of every
     plot pair is known. We compare the model's counterfactual lift (predict treated - predict control,
     same field) with the observed paired lift. This checks the number the app shows as "lift".
  3. Season normals per crop (median rainfall, GDD, NDVI, temperature of the training data) and the
     single trial dose per crop. The app feeds these to the model instead of fixed constants, so its
     inputs stay inside the range the model was trained on.

Run from the repo root:  python pipeline/evaluate_model.py
Writes:                  models/per_crop_metrics.json, models/season_normals.json
"""

import json
import os

import joblib
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _r2(y, p):
    ss_res = float(np.sum((y - p) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def main():
    df = pd.read_csv(os.path.join(ROOT, "data", "field_trials.csv"))
    schema = json.load(open(os.path.join(ROOT, "models", "feature_schema.json"), encoding="utf-8"))
    cols = schema["encoded_columns"]
    model = joblib.load(os.path.join(ROOT, "models", "model.pkl"))
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1

    enc = pd.get_dummies(df, columns=["crop_type", "region"], drop_first=False)
    for c in cols:
        if c not in enc.columns:
            enc[c] = 0.0
    X = enc[cols].astype(float)
    df["pred"] = model.predict(X)

    test = df[df["year"] == 2025].copy()

    # 1. per-crop accuracy on the held-out season
    per_crop = {}
    for crop, g in test.groupby("crop"):
        y, p = g["yield"].to_numpy(), g["pred"].to_numpy()
        mae = float(np.mean(np.abs(y - p)))
        per_crop[crop] = {
            "n_test": int(len(g)),
            "mean_yield_q_acre": round(float(np.mean(y)), 2),
            "r2": round(_r2(y, p), 3),
            "mae_q_acre": round(mae, 2),
            "rmse_q_acre": round(float(np.sqrt(np.mean((y - p) ** 2))), 2),
            "mae_pct_of_mean": round(100.0 * mae / float(np.mean(y)), 1),
        }

    # 2. treatment-effect recovery on held-out pairs (same field, control vs treated)
    pairs = test.pivot_table(index="experiment_id", columns="bio_applied", values=["yield", "pred"], aggfunc="first").dropna()
    crop_of = test.drop_duplicates("experiment_id").set_index("experiment_id")["crop"]
    obs_lift = pairs[("yield", 1)] - pairs[("yield", 0)]
    mod_lift = pairs[("pred", 1)] - pairs[("pred", 0)]
    lift = {"overall": {
        "n_pairs": int(len(pairs)),
        "mean_observed_lift_q_acre": round(float(obs_lift.mean()), 3),
        "mean_model_lift_q_acre": round(float(mod_lift.mean()), 3),
        "lift_mae_q_acre": round(float(np.mean(np.abs(obs_lift - mod_lift))), 3),
        "lift_correlation": round(float(np.corrcoef(obs_lift, mod_lift)[0, 1]), 3) if len(pairs) > 2 else None,
    }}
    for crop in sorted(set(crop_of)):
        ids = crop_of[crop_of == crop].index.intersection(pairs.index)
        if len(ids) == 0:
            continue
        o, m = obs_lift.loc[ids], mod_lift.loc[ids]
        lift[crop] = {
            "n_pairs": int(len(ids)),
            "mean_observed_lift_q_acre": round(float(o.mean()), 3),
            "mean_model_lift_q_acre": round(float(m.mean()), 3),
            "lift_mae_q_acre": round(float(np.mean(np.abs(o - m))), 3),
        }

    pooled = {
        "r2": round(_r2(test["yield"].to_numpy(), test["pred"].to_numpy()), 4),
        "mae_q_acre": round(float(np.mean(np.abs(test["yield"] - test["pred"]))), 2),
        "note": "Pooled across crops; dominated by the gap between crop yield scales. Use the per-crop numbers.",
    }
    r2s = [v["r2"] for v in per_crop.values()]
    out = {
        "data": "SIMULATED (pipeline/offline_training_pipeline.py, seed 42). Not real field trials.",
        "split": "train 2021-2024, test 2025 (held-out season)",
        "pooled": pooled,
        "within_crop_r2_range": [min(r2s), max(r2s)],
        "per_crop": per_crop,
        "treatment_effect": lift,
    }
    json.dump(out, open(os.path.join(ROOT, "models", "per_crop_metrics.json"), "w", encoding="utf-8"), indent=2)

    # 3. season normals the app feeds to the model (training-data medians), plus the trial dose
    treated = df[df["bio_applied"] == 1]
    normals = {}
    for crop, g in df.groupby("crop"):
        normals[crop] = {
            "rainfall_mm": round(float(g["cumulative_rainfall_mm"].median()), 1),
            "gdd": round(float(g["growing_degree_days"].median()), 1),
            "ndvi": round(float(g["peak_ndvi"].median()), 3),
            "temp_c_p05": round(float(g["avg_temperature_c"].quantile(0.05)), 1),
            "temp_c_p95": round(float(g["avg_temperature_c"].quantile(0.95)), 1),
            "trial_dose": round(float(treated[treated["crop"] == crop]["bio_dosage_l_ha"].median()), 2),
        }
    json.dump({"source": "Medians of data/field_trials.csv (simulated) per crop", "crops": normals},
              open(os.path.join(ROOT, "models", "season_normals.json"), "w", encoding="utf-8"), indent=2)

    print(f"pooled R2 {pooled['r2']}  |  within-crop R2 {min(r2s)} .. {max(r2s)}")
    for c, v in sorted(per_crop.items()):
        print(f"  {c:28s} R2 {v['r2']:7.3f}  MAE {v['mae_q_acre']:6.2f} q/acre ({v['mae_pct_of_mean']}% of mean)")
    o = lift["overall"]
    print(f"lift: observed {o['mean_observed_lift_q_acre']} vs model {o['mean_model_lift_q_acre']} q/acre, "
          f"MAE {o['lift_mae_q_acre']}, corr {o['lift_correlation']}")


if __name__ == "__main__":
    main()
