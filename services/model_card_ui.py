"""
model_card_ui.py - the honest model card on the YIELD tab.

Shows what the model can and cannot claim:
  * accuracy per crop on the held-out 2025 season (not the pooled R², which mostly separates crops),
  * how well the model's with/without lift matches the paired plots it never saw,
  * the difference between SHAP (why the model predicts this), the counterfactual lift (what the model
    estimates the product adds) and causal proof (which needs real paired or randomised trials).
Numbers come from models/per_crop_metrics.json, written by pipeline/evaluate_model.py.
"""

import html as html_mod

import pandas as pd
import streamlit as st

from services import economics


def _e(x) -> str:
    return html_mod.escape(str(x))


def render_model_card(crop: str, version: str, attribution: dict) -> None:
    rep = economics.model_report()
    if not rep:
        st.info("Run `python pipeline/evaluate_model.py` to create the per-crop model report.")
        return
    pc = rep.get("per_crop", {})
    me = pc.get(crop, {})
    te = rep.get("treatment_effect", {})
    te_c = te.get(crop, {})
    lo, hi = rep.get("within_crop_r2_range", [None, None])
    pooled = rep.get("pooled", {})

    st.markdown(f"""
<div class="aa-card" style="margin-top:18px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
    <strong style="color:#0f172a;font-size:0.98rem;">🔬 Model card ({_e(version)}) — how far to trust these numbers</strong>
    <span style="background:#fff7ed;border:1px solid #fdba74;color:#9a3412;font-size:0.72rem;font-weight:800;padding:3px 10px;border-radius:12px;">
      SIMULATED TRAINING DATA · NOT FIELD-VALIDATED</span>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;">
    <div class="aa-mini"><div class="aa-mini-k">{_e(crop.split(' (')[0])}: typical error</div>
      <div class="aa-mini-v">±{me.get('mae_q_acre', 0):.2f} q/acre</div>
      <div class="aa-mini-s">{me.get('mae_pct_of_mean', 0):.1f}% of the crop's average yield</div></div>
    <div class="aa-mini"><div class="aa-mini-k">{_e(crop.split(' (')[0])}: R² within the crop</div>
      <div class="aa-mini-v">{me.get('r2', 0):.2f}</div>
      <div class="aa-mini-s">{me.get('n_test', 0)} held-out 2025 plots</div></div>
    <div class="aa-mini"><div class="aa-mini-k">Lift error ({_e(crop.split(' (')[0])})</div>
      <div class="aa-mini-v">±{te_c.get('lift_mae_q_acre', 0):.2f} q/acre</div>
      <div class="aa-mini-s">model lift vs. paired plots it never saw</div></div>
    <div class="aa-mini"><div class="aa-mini-k">Pooled R² (all crops)</div>
      <div class="aa-mini-v">{pooled.get('r2', 0):.3f}</div>
      <div class="aa-mini-s">misleading alone: within-crop R² is {lo:.2f} to {hi:.2f}</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("""
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-top:10px;">
  <div class="aa-mini" style="text-align:left;"><div class="aa-mini-k">1 · SHAP waterfall (above)</div>
    <div class="aa-mini-s" style="font-size:.82rem;">Explains <b>why the model</b> predicts this yield. It is feature attribution:
    it does not show that a product <i>caused</i> anything.</div></div>
  <div class="aa-mini" style="text-align:left;"><div class="aa-mini-k">2 · Counterfactual lift</div>
    <div class="aa-mini-s" style="font-size:.82rem;">The same field predicted with and without the biological. It is the model's
    <b>estimate</b> of the treatment effect, checked against held-out paired plots.</div></div>
  <div class="aa-mini" style="text-align:left;"><div class="aa-mini-k">3 · Causal proof (not claimed)</div>
    <div class="aa-mini-s" style="font-size:.82rem;">Needs real paired treated/untreated strips or randomised trials on farms.
    The Season Journal collects exactly that, so the model can be re-trained on real plots.</div></div>
</div>""", unsafe_allow_html=True)

    if attribution:
        td, f = attribution.get("trial_dose"), attribution.get("dose_factor", 1.0)
        if f is not None and f < 0.999:
            st.caption(f"Dose: the trials used {td:.1f} L per crop, so the model only knows that dose. At your dose "
                       f"we credit {f * 100:.0f}% of the lift (assumed linear up to the trial dose, no extra gain above it).")
        else:
            st.caption(f"Dose: the trials used {td:.1f} L. More than that is not credited with more yield; it only adds cost.")

    with st.expander("Accuracy for every crop (held-out 2025 season)"):
        rows = []
        for c, v in sorted(pc.items()):
            t = te.get(c, {})
            rows.append({"Crop": c, "Plots": v["n_test"], "Avg yield (q/acre)": v["mean_yield_q_acre"],
                         "R² within crop": v["r2"], "Typical error (q/acre)": v["mae_q_acre"],
                         "Error % of avg": v["mae_pct_of_mean"],
                         "Observed lift": t.get("mean_observed_lift_q_acre"), "Model lift": t.get("mean_model_lift_q_acre"),
                         "Lift error": t.get("lift_mae_q_acre")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(f"{rep.get('data', '')} Split: {rep.get('split', '')}. Reproduce with `python pipeline/evaluate_model.py`.")
