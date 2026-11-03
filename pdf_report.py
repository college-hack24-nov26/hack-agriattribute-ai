"""
pdf_report.py - printable A4 advisory report (yield attribution + ROI).

generate_advisory_pdf() returns the PDF as bytes, ready for st.download_button.
Text is restricted to Latin-1 (built-in PDF fonts), so rupees are written as "Rs".
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

GREEN = (4, 120, 87)
DARK = (15, 42, 33)
MUTED = (75, 99, 88)
LIGHT = (236, 253, 245)


def _t(value: Any) -> str:
    """Latin-1 safe text (built-in fonts cannot render other scripts)."""
    text = str(value).replace("₹", "Rs ").replace("−", "-").replace("±", "+/-")
    return text.encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    def header(self):
        self.set_fill_color(*GREEN)
        self.rect(0, 0, 210, 22, style="F")
        self.set_xy(10, 6)
        self.set_font("helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "AgriAttribute AI - Yield Attribution & ROI Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(28)

    def footer(self):
        self.set_y(-14)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 8, f"Advisory estimate - verify with a local agronomist. Page {self.page_no()}", align="C")


def _section(pdf: FPDF, title: str):
    pdf.ln(3)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 8, _t(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*GREEN)
    pdf.line(pdf.l_margin, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(*DARK)


def _kv_rows(pdf: FPDF, rows: List[tuple], bold_value: bool = False):
    for key, val in rows:
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(*MUTED)
        pdf.cell(62, 7, _t(key))
        pdf.set_font("helvetica", "B" if bold_value else "", 10)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _t(val), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _table(pdf: FPDF, headers: List[str], rows: List[List[Any]], widths: List[float]):
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_fill_color(*LIGHT)
    pdf.set_text_color(*DARK)
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, _t(h), border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("helvetica", "", 8.5)
    for row in rows:
        for val, w in zip(row, widths):
            pdf.cell(w, 7.5, _t(val), border=1, align="C")
        pdf.ln()


def generate_advisory_pdf(
    crop: str,
    region: str,
    location: str,
    bio_product: str,
    dosage_l_acre: float,
    summary: Dict[str, float],
    scenarios: List[Dict[str, Any]],
    shap_attr: Optional[Dict[str, Any]] = None,
    model_note: str = "",
) -> bytes:
    """
    summary keys: yield_q_acre, untreated_yield_q_acre, lift_q_acre, gross_revenue, input_cost,
                  net_profit, roi_pct, price_per_q
    scenarios: rows from decision_simulator.simulate_5_scenarios()["scenarios"]
    shap_attr: output of decision_simulator.compute_shap_attribution() (optional)
    """
    pdf = _Report(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    _section(pdf, "Field profile")
    _kv_rows(pdf, [
        ("Crop", crop),
        ("Agro-climatic belt", region),
        ("Location", location),
        ("Biological input", f"{bio_product} @ {dosage_l_acre:g} L/acre"),
        ("Report date", datetime.now().strftime("%d %b %Y")),
    ])

    _section(pdf, "Outcome per acre")
    s = summary
    _kv_rows(pdf, [
        ("Predicted yield (treated)", f"{s['yield_q_acre']:.1f} q/acre"),
        ("Counterfactual yield (untreated)", f"{s['untreated_yield_q_acre']:.1f} q/acre"),
        ("Biological yield lift", f"{s['lift_q_acre']:+.2f} q/acre"),
        ("Mandi price used", f"Rs {s['price_per_q']:,.0f} / quintal"),
        ("Revenue from yield lift", f"Rs {s['gross_revenue']:,.0f}"),
        ("Input cost (biological + fertilizer)", f"Rs {s['input_cost']:,.0f}"),
        ("Net profit from the lift", f"Rs {s['net_profit']:,.0f}"),
        ("ROI on input cost", f"{s['roi_pct']:.0f}%"),
    ], bold_value=True)

    if shap_attr:
        _section(pdf, "Why this yield? (TreeSHAP attribution)")
        g = shap_attr["groups"]
        start = shap_attr["base_value"] + g["baseline"]["q_acre"]
        _kv_rows(pdf, [
            ("Crop & regional baseline", f"{start:.1f} q/acre"),
            ("Soil fertility", f"{g['soil']['q_acre']:+.2f} q/acre"),
            ("Weather & climate", f"{g['weather']['q_acre']:+.2f} q/acre"),
            ("Biological treatment", f"{g['biological']['q_acre']:+.2f} q/acre"),
            ("= Predicted yield", f"{shap_attr['prediction']:.1f} q/acre"),
        ])
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(0, 4.5, _t("Contributions are exact TreeSHAP values relative to the model's average conditions and add up to the predicted yield."))

    if scenarios:
        _section(pdf, "Decision scenarios (per acre)")
        rows = []
        for sc in scenarios:
            rows.append([
                sc.get("scenario", ""),
                f"{sc.get('expected_yield_q_acre', 0):.1f}",
                f"Rs {sc.get('gross_revenue_inr', 0):,.0f}",
                f"Rs {sc.get('total_input_cost_inr', 0):,.0f}",
                f"Rs {sc.get('net_profit_inr', 0):,.0f}",
                f"{sc.get('roi_pct', 0):.0f}%",
            ])
        _table(pdf, ["Scenario", "Yield (q/ac)", "Lift revenue", "Input cost", "Net profit", "ROI"],
               rows, [58, 24, 30, 30, 30, 18])

    _section(pdf, "Important notes")
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    notes = model_note or (
        "Estimates come from a Random Forest model trained on a synthetic field-trial dataset; "
        "treat them as decision support, not a guarantee of yield or profit."
    )
    pdf.multi_cell(0, 4.8, _t(notes))

    return bytes(pdf.output())
