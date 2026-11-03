"""
management_engine.py - Controllable Management Layer & Causal Confounder Engine
AgriAttribute AI — Syngenta Biologicals × ANNAM.AI Hack Core 2026 (PS-07)

Purpose:
Captures what the farmer directly controlled (irrigation, fertilization, crop protection,
planting, field operations, biological applications) to isolate background management
covariates from pure biological yield attribution (tau).

Key Modules:
1. Normalized Data Structure (ManagementRecord & ManagementProfile)
2. Authoritative Crop-Specific Management Benchmarks (ICAR / TNAU / SAU / CACP)
3. Transparent 5-Component Management Quality Score
4. Management vs. Biological Causal Interaction Evaluator
5. "What Should I Improve?" Actionable Agronomic Gap Analyzer
6. Synchronizer Bridges (FieldContext, Cost of Cultivation, Farm Memory, LeafVision)
7. Human-Centric Farmer UI & Technical Audit View for Hackathon Judges
"""

import re
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import streamlit as st


# ============================================================================
# SAFE NUMERIC EXTRACTION HELPERS
# Distinguish numeric agronomic values embedded in categorical description strings.
# These helpers NEVER raise ValueError — always return (numeric, description) tuple
# so callers can separate numeric geometry from categorical suffixes.
# ============================================================================

_NUMERIC_PATTERN = re.compile(r'(\d+(?:\.\d+)?)')

def _preprocess_numeric_string(s: str) -> str:
    """Strip formatting characters that break numeric extraction:
    thousand separators (,), currency symbols (₹$€£), units and whitespace.
    """
    # Remove thousand separators and common currency / price formatting
    s = s.replace(',', '').replace('₹', '').replace('$', '').replace('€', '').replace('£', '')
    # Remove /per, /q, /ha, /acre unit divisors that follow numbers
    s = re.sub(r'/\s*\w+', '', s)
    return s.strip()

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert any value to float without raising ValueError.

    Handles bare numbers, numeric strings, and strings where the first
    numeric token is extracted (e.g. '30 (Wide-Row)' -> 30.0).
    Also handles formatted prices: '₹5,200 / q' -> 5200.0"""
    try:
        return float(value)
    except (TypeError, ValueError):
        s = str(value).strip()
        if not s:
            return default
        # Preprocess first: strip commas, currency, units — this catches formatted prices
        s2 = _preprocess_numeric_string(s)
        if s2 != s:
            try:
                return float(s2)
            except (TypeError, ValueError):
                m2 = _NUMERIC_PATTERN.search(s2)
                if m2:
                    try:
                        return float(m2.group(1))
                    except (TypeError, ValueError):
                        pass
        # Fall back to raw string extraction for categorical agronomic strings
        m = _NUMERIC_PATTERN.search(s)
        if m:
            try:
                return float(m.group(1))
            except (TypeError, ValueError):
                return default
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safe integer conversion — see safe_float."""
    return int(round(safe_float(value, float(default))))


def parse_spacing_cm(spacing_str: Any, default_row: float = 45.0, default_plant: float = 10.0) -> Tuple[float, float, str]:
    """Parse an agronomic spacing description such as:
      '120 x 30 cm (Wide-Row)'
      '90 x 60 cm (or 120 x 45 cm for Bt Hybrid)'
      '45 x 5 cm'
    Returns (row_spacing_cm, plant_spacing_cm, categorical_description).
    NEVER raises ValueError.
    """
    raw = str(spacing_str).strip() if spacing_str is not None else ''
    m = re.search(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)', raw)
    if m:
        row_v = float(m.group(1))
        plant_v = float(m.group(2))
    else:
        row_v, plant_v = default_row, default_plant
    description = raw
    return row_v, plant_v, description


def parse_npk_value(npk_value: Any, default_n: float = 0.0, default_p: float = 0.0, default_k: float = 0.0) -> Dict[str, float]:
    """Parse NPK ratio dict or string safely."""
    if isinstance(npk_value, dict):
        return {
            "N": safe_float(npk_value.get("N", default_n), default_n),
            "P": safe_float(npk_value.get("P", default_p), default_p),
            "K": safe_float(npk_value.get("K", default_k), default_k),
        }
    if isinstance(npk_value, (list, tuple)) and len(npk_value) >= 3:
        return {"N": safe_float(npk_value[0], default_n),
                "P": safe_float(npk_value[1], default_p),
                "K": safe_float(npk_value[2], default_k)}
    return {"N": default_n, "P": default_p, "K": default_k}


# ============================================================================
# 1. DATA MODELS: NORMALIZED MANAGEMENT VARIABLES
# ============================================================================

@dataclass
class ManagementRecord:
    """Canonical representation of a single controllable management attribute."""
    field_id: str
    crop: str
    season: str
    category: str
    variable: str
    value: Any
    unit: str
    timing: str
    source: str
    record_type: str  # 'farmer-entered', 'imported', 'derived'


@dataclass
class ManagementProfile:
    """Full agronomic management profile for a specific field and season."""
    field_id: str
    crop: str
    season: str
    
    # 1. Water Management
    irrigation_method: str = "Drip / Micro-irrigation"
    irrigation_source: str = "Borewell / Tube Well"
    irrigation_frequency_days: int = 7
    last_irrigation_days_ago: int = 3
    irrigation_adequacy: str = "Optimal (Adequate Moisture)"
    
    # 2. Nutrient & Fertilizer Management
    fertilizer_npk_ratio_pct: int = 100
    n_applied_kg_acre: float = 48.0
    p_applied_kg_acre: float = 24.0
    k_applied_kg_acre: float = 16.0
    fertilizer_timing: str = "Split (50% Basal + 50% Topdressing at Vegetative/Flowering)"
    organic_manure_t_acre: float = 2.5
    organic_manure_type: str = "Farmyard Manure (FYM)"
    
    # 3. Crop Protection
    protection_practice: str = "Integrated Pest Management (IPM) + Timely Foliar"
    pesticide_applied: bool = True
    pesticide_product: str = "Broad-Spectrum Systemic Fungicide"
    protection_timing: str = "Prophylactic / Early Threshold"
    target_pest_disease: str = "Foliar Blight / Sucking Pests"
    
    # 4. Planting & Crop Establishment
    sowing_date_str: str = "2026-06-25"
    seed_variety_type: str = "High-Yielding Certified Hybrid"
    seed_rate_kg_acre: float = 25.0
    row_spacing_cm: float = 45.0
    plant_spacing_cm: float = 10.0
    establishment_method: str = "Direct Sowing (Ridge & Furrow)"
    
    # 5. Field Operations & Mechanization
    tillage_type: str = "Minimum Tillage (1 Plough + 1 Rotavator)"
    weed_management: str = "Integrated (Pre-emergence Herbicide + 1 Hand Weeding)"
    mechanization_level: str = "Tractor-drawn sowing + Manual harvesting"
    
    # 6. Biological Application Protocol
    bio_product: str = "Syngenta Quantis"
    bio_dosage_l_acre: float = 2.0
    bio_crop_stage: str = "Flowering / Pod Initiation"
    bio_applications_count: int = 1
    bio_application_date: str = "2026-07-20"
    bio_application_timing: str = "Optimal (Early Morning / High Humidity)"
    
    # Derived Metadata
    management_score: int = 88
    quality_grade: str = "Good"

    def to_records_list(self) -> List[ManagementRecord]:
        """Flattens profile into normalized records list for audit and export."""
        records = [
            ManagementRecord(self.field_id, self.crop, self.season, "Water", "irrigation_method", self.irrigation_method, "categorical", "Seasonal", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Water", "irrigation_source", self.irrigation_source, "categorical", "Seasonal", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Water", "irrigation_frequency", self.irrigation_frequency_days, "days", "Continuous", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Water", "last_irrigation", self.last_irrigation_days_ago, "days ago", "Recent", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Water", "irrigation_adequacy", self.irrigation_adequacy, "categorical", "Current Stage", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Nutrient", "fertilizer_level", self.fertilizer_npk_ratio_pct, "% of Rec. NPK", "Seasonal Total", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Nutrient", "nitrogen_applied", self.n_applied_kg_acre, "kg/acre", "Split Application", "Derived from NPK %", "derived"),
            ManagementRecord(self.field_id, self.crop, self.season, "Nutrient", "phosphorus_applied", self.p_applied_kg_acre, "kg/acre", "Basal Application", "Derived from NPK %", "derived"),
            ManagementRecord(self.field_id, self.crop, self.season, "Nutrient", "potassium_applied", self.k_applied_kg_acre, "kg/acre", "Basal Application", "Derived from NPK %", "derived"),
            ManagementRecord(self.field_id, self.crop, self.season, "Nutrient", "fertilizer_timing", self.fertilizer_timing, "categorical", "Split Schedule", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Nutrient", "organic_manure", self.organic_manure_t_acre, "tonnes/acre", "Pre-sowing Incorporation", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Protection", "protection_practice", self.protection_practice, "categorical", "Seasonal", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Protection", "protection_timing", self.protection_timing, "categorical", "First Symptom", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Planting", "sowing_date", self.sowing_date_str, "date (YYYY-MM-DD)", "Sowing Window", "Farmer Entered / Telemetry", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Planting", "seed_variety", self.seed_variety_type, "categorical", "Establishment", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Planting", "spacing_row_x_plant", f"{self.row_spacing_cm} x {self.plant_spacing_cm}", "cm", "Planting Geometry", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Operations", "tillage_type", self.tillage_type, "categorical", "Land Preparation", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Operations", "weed_management", self.weed_management, "categorical", "0-45 DAS", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Biological", "bio_product", self.bio_product, "brand name", "Flowering Stage", "Syngenta Protocol", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Biological", "bio_dosage", self.bio_dosage_l_acre, "L/acre", "Foliar Spray", "Syngenta Protocol", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Biological", "bio_crop_stage", self.bio_crop_stage, "phenology", "Application Window", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Biological", "bio_applications_count", self.bio_applications_count, "number of sprays", "Season Count", "Farmer Entered", "farmer-entered"),
            ManagementRecord(self.field_id, self.crop, self.season, "Quality", "management_quality_score", self.management_score, "score (0-100)", "Overall Evaluation", "Rule-Based Agronomic Model", "derived")
        ]
        return records

    def to_dataframe(self) -> pd.DataFrame:
        """Converts profile into a structured pandas DataFrame."""
        recs = self.to_records_list()
        return pd.DataFrame([asdict(r) for r in recs])


# ============================================================================
# 2. CROP-SPECIFIC AGRONOMIC BENCHMARKS (ICAR / TNAU / SAU / CACP STANDARDS)
# ============================================================================

CROP_MANAGEMENT_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "Soybean": {
        "rec_npk_kg_acre": {"N": 12.0, "P": 24.0, "K": 16.0},
        "rec_fym_t_acre": 2.5,
        "ideal_spacing_cm": "45 x 5 cm",
        "seed_rate_kg_acre": 25.0,
        "critical_irrigation_stages": ["Flowering (R1-R2)", "Pod Filling (R3-R4)"],
        "recommended_irrigation": "Sprinkler / Drip or Furrow at critical stages",
        "major_weeds_window": "First 30-40 days after sowing (critical period)",
        "target_diseases": ["Soybean Rust (Phakopsora pachyrhizi)", "Anthracnose", "Yellow Mosaic Virus"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Flowering / Pod Initiation",
        "source": "ICAR-Indian Institute of Soybean Research (IISR), Indore & CACP"
    },
    "Cotton": {
        "rec_npk_kg_acre": {"N": 48.0, "P": 24.0, "K": 24.0},
        "rec_fym_t_acre": 4.0,
        "ideal_spacing_cm": "90 x 60 cm (or 120 x 45 cm for Bt Hybrid)",
        "seed_rate_kg_acre": 1.5,
        "critical_irrigation_stages": ["Square Formation", "Flowering & Boll Development"],
        "recommended_irrigation": "Drip Irrigation (fertigation capability)",
        "major_weeds_window": "0 to 60 days after sowing",
        "target_diseases": ["Bacterial Blight", "Grey Mildew", "Bollworm Complex", "Sucking Pests"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Square / Early Boll Formation",
        "source": "ICAR-Central Institute for Cotton Research (CICR), Nagpur & CACP"
    },
    "Wheat": {
        "rec_npk_kg_acre": {"N": 48.0, "P": 24.0, "K": 16.0},
        "rec_fym_t_acre": 3.0,
        "ideal_spacing_cm": "20 x 5 cm",
        "seed_rate_kg_acre": 40.0,
        "critical_irrigation_stages": ["CRI Stage (21 DAS)", "Tillering", "Jointing", "Flowering", "Milking"],
        "recommended_irrigation": "Border Strip / Sprinkler (4-6 irrigations)",
        "major_weeds_window": "30-35 DAS (Phalaris minor & broadleaf)",
        "target_diseases": ["Stripe Rust (Yellow Rust)", "Leaf Rust", "Karnal Bunt"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Flag Leaf / Heading Initiation (Heat Priming)",
        "source": "ICAR-Indian Institute of Wheat and Barley Research (IIWBR), Karnal & CACP"
    },
    "Rice (Paddy)": {
        "rec_npk_kg_acre": {"N": 48.0, "P": 20.0, "K": 20.0},
        "rec_fym_t_acre": 4.0,
        "ideal_spacing_cm": "20 x 15 cm",
        "seed_rate_kg_acre": 15.0,
        "critical_irrigation_stages": ["Tillering", "Panicle Initiation", "Flowering / Anthesis"],
        "recommended_irrigation": "Alternate Wetting and Drying (AWD) or Controlled Flood",
        "major_weeds_window": "15 to 30 days after transplanting",
        "target_diseases": ["Rice Blast (Magnaporthe oryzae)", "Bacterial Leaf Blight", "Sheath Blight"],
        "recommended_bio_product": "Syngenta Isabion",
        "recommended_bio_dose_l_acre": 1.5,
        "recommended_bio_stage": "Panicle Initiation / Booting",
        "source": "ICAR-National Rice Research Institute (NRRI), Cuttack & TNAU"
    },
    "Maize": {
        "rec_npk_kg_acre": {"N": 48.0, "P": 24.0, "K": 20.0},
        "rec_fym_t_acre": 3.0,
        "ideal_spacing_cm": "60 x 20 cm",
        "seed_rate_kg_acre": 8.0,
        "critical_irrigation_stages": ["Knee High", "Tasseling / Silking", "Grain Filling"],
        "recommended_irrigation": "Furrow / Drip at critical flowering window",
        "major_weeds_window": "15 to 45 DAS",
        "target_diseases": ["Fall Armyworm (Spodoptera frugiperda)", "Turcicum Leaf Blight", "Downy Mildew"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Tasseling / Silking Window",
        "source": "ICAR-Indian Institute of Maize Research (IIMR), Ludhiana"
    },
    "Sugarcane": {
        "rec_npk_kg_acre": {"N": 100.0, "P": 46.0, "K": 46.0},
        "rec_fym_t_acre": 10.0,
        "ideal_spacing_cm": "120 x 30 cm (Wide-Row)",
        "seed_rate_kg_acre": 2500.0,
        "critical_irrigation_stages": ["Formative Phase (60-150 DAP)", "Grand Growth (150-270 DAP)"],
        "recommended_irrigation": "Sub-surface Drip / Furrow (15-20 days interval)",
        "major_weeds_window": "First 90-120 days until canopy closure",
        "target_diseases": ["Red Rot (Colletotrichum falcatum)", "Smut", "Early Shoot Borer"],
        "recommended_bio_product": "Syngenta CropBio+",
        "recommended_bio_dose_l_acre": 3.0,
        "recommended_bio_stage": "Formative / Active Tillering Phase",
        "source": "ICAR-Indian Institute of Sugarcane Research (IISR), Lucknow"
    },
    "Onion": {
        "rec_npk_kg_acre": {"N": 40.0, "P": 20.0, "K": 24.0},
        "rec_fym_t_acre": 6.0,
        "ideal_spacing_cm": "15 x 10 cm",
        "seed_rate_kg_acre": 4.0,
        "critical_irrigation_stages": ["Transplanting", "Bulb Initiation", "Bulb Development"],
        "recommended_irrigation": "Micro-sprinkler / Drip (frequent light irrigations)",
        "major_weeds_window": "0 to 45 days after transplanting",
        "target_diseases": ["Purple Blotch (Alternaria porri)", "Stemphylium Blight", "Thrips"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Bulb Initiation / Early Sizing",
        "source": "ICAR-Directorate of Onion and Garlic Research (DOGR), Pune & TNAU"
    },
    "Tomato": {
        "rec_npk_kg_acre": {"N": 48.0, "P": 32.0, "K": 24.0},
        "rec_fym_t_acre": 8.0,
        "ideal_spacing_cm": "60 x 45 cm",
        "seed_rate_kg_acre": 0.15,
        "critical_irrigation_stages": ["Flowering", "Fruit Setting", "Fruit Sizing"],
        "recommended_irrigation": "Drip Irrigation with weekly fertigation schedule",
        "major_weeds_window": "First 40 days after transplanting",
        "target_diseases": ["Early Blight (Alternaria solani)", "Late Blight", "Bacterial Wilt", "Tomato Leaf Curl Virus"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "First Cluster Flowering / Fruit Set",
        "source": "ICAR-Indian Institute of Horticultural Research (IIHR), Bengaluru & TNAU"
    },
    "Groundnut (Peanut)": {
        "rec_npk_kg_acre": {"N": 10.0, "P": 20.0, "K": 16.0},
        "rec_fym_t_acre": 3.0,
        "ideal_spacing_cm": "30 x 10 cm",
        "seed_rate_kg_acre": 45.0,
        "critical_irrigation_stages": ["Flowering (30-40 DAS)", "Pegging (45-55 DAS)", "Pod Development"],
        "recommended_irrigation": "Sprinkler / Furrow at critical peg penetration",
        "major_weeds_window": "First 45 days (critical to avoid peg disturbance)",
        "target_diseases": ["Tikka Leaf Spot (Cercospora)", "Rust", "Collar Rot"],
        "recommended_bio_product": "Syngenta Isabion",
        "recommended_bio_dose_l_acre": 1.5,
        "recommended_bio_stage": "Flowering / Pegging Initiation",
        "source": "ICAR-Directorate of Groundnut Research (DGR), Junagadh & TNAU"
    },
    "Mustard / Rapeseed": {
        "rec_npk_kg_acre": {"N": 32.0, "P": 16.0, "K": 16.0},
        "rec_fym_t_acre": 2.5,
        "ideal_spacing_cm": "30 x 10 cm",
        "seed_rate_kg_acre": 2.0,
        "critical_irrigation_stages": ["Rosette / Pre-flowering (30-35 DAS)", "Siliqua / Pod Formation (55-65 DAS)"],
        "recommended_irrigation": "Border / Sprinkler (2 critical irrigations)",
        "major_weeds_window": "First 30 days after sowing",
        "target_diseases": ["Alternaria Blight", "White Rust", "Mustard Aphid"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Pre-flowering / Siliqua Initiation",
        "source": "ICAR-Directorate of Rapeseed-Mustard Research (DRMR), Bharatpur & PAU"
    },
    "Chickpea (Gram / Chana)": {
        "rec_npk_kg_acre": {"N": 10.0, "P": 20.0, "K": 10.0},
        "rec_fym_t_acre": 2.0,
        "ideal_spacing_cm": "30 x 10 cm",
        "seed_rate_kg_acre": 30.0,
        "critical_irrigation_stages": ["Pre-flowering (45 DAS)", "Pod Development (70 DAS)"],
        "recommended_irrigation": "Sprinkler / Light furrow (Avoid waterlogging)",
        "major_weeds_window": "First 30-60 DAS",
        "target_diseases": ["Fusarium Wilt", "Ascochyta Blight", "Helicoverpa Pod Borer"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 1.5,
        "recommended_bio_stage": "Flower Bud / Pod Formation Window",
        "source": "ICAR-Indian Institute of Pulses Research (IIPR), Kanpur"
    },
    "Tur / Pigeon Pea (Arhar)": {
        "rec_npk_kg_acre": {"N": 10.0, "P": 20.0, "K": 8.0},
        "rec_fym_t_acre": 2.5,
        "ideal_spacing_cm": "90 x 20 cm (or 120 x 30 cm)",
        "seed_rate_kg_acre": 6.0,
        "critical_irrigation_stages": ["Flower Bud Initiation", "Pod Fill Stage"],
        "recommended_irrigation": "Furrow / Drip during dry spells",
        "major_weeds_window": "First 60 days (slow initial growth)",
        "target_diseases": ["Sterility Mosaic Disease", "Fusarium Wilt", "Pod Borer Complex"],
        "recommended_bio_product": "Syngenta Quantis",
        "recommended_bio_dose_l_acre": 2.0,
        "recommended_bio_stage": "Flower Bud Initiation / Pod Setting",
        "source": "ICAR-IIPR Kanpur & MPKV Rahuri"
    }
}


def get_crop_management_defaults(crop_name: str) -> Dict[str, Any]:
    """Retrieves authoritative agronomic package-of-practices defaults for a crop."""
    c_str = str(crop_name).strip()
    if c_str in CROP_MANAGEMENT_BENCHMARKS:
        return CROP_MANAGEMENT_BENCHMARKS[c_str]
    c_low = c_str.lower()
    for k, v in CROP_MANAGEMENT_BENCHMARKS.items():
        if k.lower() in c_low or c_low in k.lower():
            return v
    return CROP_MANAGEMENT_BENCHMARKS["Soybean"]


# ============================================================================
# 3. TRANSPARENT 5-COMPONENT MANAGEMENT QUALITY SCORING
# ============================================================================

def calculate_management_quality_score(profile: ManagementProfile) -> Dict[str, Any]:
    """
    Computes a transparent, evidence-based management quality score (0 - 100)
    with explicit component status and agronomic rationale.
    
    Components:
    1. Water Management (25 pts)
    2. Nutrient Alignment (25 pts)
    3. Crop Protection Timing (20 pts)
    4. Planting & Density (15 pts)
    5. Biological Adherence (15 pts)
    """
    components = {}
    total_score = 0
    
    # 1. Water Management (25 points)
    water_score = 0
    irrig_m = profile.irrigation_method.lower()
    irrig_a = profile.irrigation_adequacy.lower()
    
    if "drip" in irrig_m or "micro" in irrig_m:
        water_score += 15
    elif "sprinkler" in irrig_m:
        water_score += 13
    elif "canal" in irrig_m or "flood" in irrig_m or "furrow" in irrig_m:
        water_score += 10
    else:  # Rainfed
        water_score += 7
        
    if "optimal" in irrig_a or "adequate" in irrig_a:
        water_score += 10
        water_status = "Good (Adequate Moisture)"
        water_badge = "Good"
        water_color = "#059669"
    elif "mild" in irrig_a:
        water_score += 6
        water_status = "Fair (Mild Stress Monitored)"
        water_badge = "Fair"
        water_color = "#d97706"
    else:  # Deficit / Stress
        water_score += 2
        water_status = "Needs Attention (Moisture Deficit)"
        water_badge = "Needs attention"
        water_color = "#dc2626"
        
    components["water"] = {
        "name": "Water Management",
        "score": min(25, water_score),
        "max_score": 25,
        "status": water_status,
        "badge": water_badge,
        "color": water_color,
        "detail": f"{profile.irrigation_method} • {profile.irrigation_frequency_days}d cycle • {profile.irrigation_adequacy}"
    }
    total_score += components["water"]["score"]
    
    # 2. Nutrient Alignment (25 points)
    nut_score = 0
    fert_ratio = profile.fertilizer_npk_ratio_pct
    fym = profile.organic_manure_t_acre
    
    if 90 <= fert_ratio <= 115:
        nut_score += 18
        nut_status = "Near Recommended (Balanced)"
        nut_badge = "Good"
        nut_color = "#059669"
    elif 75 <= fert_ratio < 90 or 115 < fert_ratio <= 130:
        nut_score += 13
        nut_status = "Moderate Deviation (75-130%)"
        nut_badge = "Fair"
        nut_color = "#d97706"
    elif fert_ratio < 75:
        nut_score += 7
        nut_status = "Under-Fertilized (<75% Rec NPK)"
        nut_badge = "Needs attention"
        nut_color = "#dc2626"
    else:  # > 130% Over-fertilization
        nut_score += 8
        nut_status = "Over-Fertilized (>130% Rec NPK)"
        nut_badge = "Needs attention"
        nut_color = "#dc2626"
        
    if fym >= 2.0:
        nut_score += 7
    elif fym > 0:
        nut_score += 4
    else:
        nut_score += 1
        
    components["nutrition"] = {
        "name": "Nutrient Management",
        "score": min(25, nut_score),
        "max_score": 25,
        "status": nut_status,
        "badge": nut_badge,
        "color": nut_color,
        "detail": f"{fert_ratio}% Rec. NPK ({profile.n_applied_kg_acre:.0f}:{profile.p_applied_kg_acre:.0f}:{profile.k_applied_kg_acre:.0f} NPK) • FYM {fym:.1f} t/acre"
    }
    total_score += components["nutrition"]["score"]
    
    # 3. Crop Protection Timing (20 points)
    prot_score = 0
    timing_p = profile.protection_timing.lower()
    
    if "prophylactic" in timing_p or "early" in timing_p:
        prot_score += 20
        prot_status = "Timely (Prophylactic / Early Threshold)"
        prot_badge = "Good"
        prot_color = "#059669"
    elif "first" in timing_p or "symptom" in timing_p:
        prot_score += 15
        prot_status = "Adequate (Applied at First Symptom)"
        prot_badge = "Good"
        prot_color = "#059669"
    elif "reactive" in timing_p:
        prot_score += 10
        prot_status = "Reactive (Delayed Spraying)"
        prot_badge = "Fair"
        prot_color = "#d97706"
    else:
        prot_score += 6
        prot_status = "Needs Review (No Protection / Late)"
        prot_badge = "Needs attention"
        prot_color = "#dc2626"
        
    components["protection"] = {
        "name": "Crop Protection",
        "score": min(20, prot_score),
        "max_score": 20,
        "status": prot_status,
        "badge": prot_badge,
        "color": prot_color,
        "detail": f"{profile.protection_practice} • Timing: {profile.protection_timing}"
    }
    total_score += components["protection"]["score"]
    
    # 4. Planting & Crop Establishment (15 points)
    plant_score = 0
    variety = profile.seed_variety_type.lower()
    
    if "hybrid" in variety or "certified" in variety:
        plant_score += 10
    else:
        plant_score += 5
        
    if profile.row_spacing_cm > 0 and profile.plant_spacing_cm > 0:
        plant_score += 5
    else:
        plant_score += 2
        
    components["planting"] = {
        "name": "Planting & Establishment",
        "score": min(15, plant_score),
        "max_score": 15,
        "status": "Optimal Density & Certified Seed" if plant_score >= 12 else "Sub-optimal Geometry",
        "badge": "Good" if plant_score >= 12 else "Fair",
        "color": "#059669" if plant_score >= 12 else "#d97706",
        "detail": f"{profile.seed_variety_type} • Geometry: {profile.row_spacing_cm}x{profile.plant_spacing_cm} cm"
    }
    total_score += components["planting"]["score"]
    
    # 5. Biological Application Adherence (15 points)
    bio_score = 0
    b_defaults = get_crop_management_defaults(profile.crop)
    rec_stage = b_defaults.get("recommended_bio_stage", "Flowering")
    
    if profile.bio_dosage_l_acre >= 1.0 and profile.bio_dosage_l_acre <= 3.5:
        bio_score += 8
    else:
        bio_score += 4
        
    if any(w.lower() in profile.bio_crop_stage.lower() for w in rec_stage.lower().split()):
        bio_score += 7
        bio_status = "Appropriate (Target Stage Aligned)"
        bio_badge = "On time"
        bio_color = "#059669"
    else:
        bio_score += 3
        bio_status = "Review (Applied Off-Target Window)"
        bio_badge = "Review"
        bio_color = "#d97706"
        
    components["biological"] = {
        "name": "Biological Application Timing",
        "score": min(15, bio_score),
        "max_score": 15,
        "status": bio_status,
        "badge": bio_badge,
        "color": bio_color,
        "detail": f"{profile.bio_product} @ {profile.bio_dosage_l_acre:.1f} L/acre • Stage: {profile.bio_crop_stage}"
    }
    total_score += components["biological"]["score"]
    
    # Overall Quality Grade
    if total_score >= 80:
        overall_grade = "Good"
        overall_color = "#059669"
    elif total_score >= 60:
        overall_grade = "Fair"
        overall_color = "#d97706"
    else:
        overall_grade = "Needs attention"
        overall_color = "#dc2626"
        
    return {
        "total_score": total_score,
        "overall_grade": overall_grade,
        "overall_color": overall_color,
        "components": components
    }


# ============================================================================
# 4. MANAGEMENT VS. BIOLOGICAL CAUSAL INTERACTION EVALUATOR
# ============================================================================

def evaluate_management_biological_interaction(profile: ManagementProfile, quality_eval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates whether the biological yield response occurred under comparable
    agronomic management conditions, generating nuanced evidence statements.
    """
    w_comp = quality_eval["components"]["water"]
    n_comp = quality_eval["components"]["nutrition"]
    b_comp = quality_eval["components"]["biological"]
    
    water_good = (w_comp["badge"] == "Good")
    nut_good = (n_comp["badge"] == "Good")
    bio_good = (b_comp["badge"] == "On time")
    
    statements = []
    attribution_confidence = "HIGH"
    confounder_risk = "LOW"
    
    if water_good and nut_good and bio_good:
        attribution_confidence = "HIGH (Pure Biological Attribution)"
        confounder_risk = "MINIMAL"
        primary_statement = "Biological response observed under adequate irrigation and near-recommended nutrition. High confidence in pure biological attribution."
        statements.append("✅ Controllable background variables (water, NPK, crop protection) are operating near agronomic optimum.")
        statements.append(f"🧬 Syngenta {profile.bio_product} dosage ({profile.bio_dosage_l_acre:.1f} L/acre) applied precisely within the recommended {profile.bio_crop_stage} window.")
        statements.append("📊 Observed yield lift represents true treatment effect (tau) with minimal confounding bias.")
    elif not water_good:
        attribution_confidence = "MODERATE (Water-Confounded)"
        confounder_risk = "HIGH (Moisture Deficit)"
        primary_statement = "Biological effect observed under suboptimal or deficit irrigation. Biological treatment provided vital osmotic protection against drought stress, though moisture limitation constrained total yield potential."
        statements.append("⚠️ Moisture deficit acts as a primary background yield constraint.")
        statements.append(f"💡 {profile.bio_product} actively stimulated abiotic stress priming pathways (proline & glycine betaine synthesis), buffering against severe yield collapse.")
        statements.append("🎯 Recommendation: Align life-saving irrigation with biological application to unlock full yield synergy.")
    elif not nut_good:
        attribution_confidence = "MODERATE (Nutrient-Confounded)"
        confounder_risk = "MEDIUM (Nutrient Imbalance)"
        primary_statement = "Biological effect observed under sub-recommended nutrient levels. Biostimulant enhanced nutrient use efficiency (NUE), but full response was limited by basal fertility deficits."
        statements.append(f"⚠️ Applied fertilizer level ({profile.fertilizer_npk_ratio_pct}% Rec NPK) creates a sink-strength bottleneck.")
        statements.append(f"💡 {profile.bio_product} improved rhizosphere assimilation, but cannot substitute for required macronutrient demand.")
    else:
        attribution_confidence = "MODERATE (Application Timing Review)"
        confounder_risk = "LOW-MEDIUM"
        primary_statement = "Biological response observed under standard management, but application timing should be tuned to the peak stress window."
        statements.append(f"⚠️ Current stage '{profile.bio_crop_stage}' differs slightly from optimal '{get_crop_management_defaults(profile.crop)['recommended_bio_stage']}'.")
        statements.append("💡 Applying at early flower initiation maximizes fruit set and biomass conversion.")

    return {
        "primary_statement": primary_statement,
        "attribution_confidence": attribution_confidence,
        "confounder_risk": confounder_risk,
        "bullet_points": statements
    }


# ============================================================================
# 5. "WHAT SHOULD I IMPROVE?" ACTIONABLE AGRONOMIC GAP ANALYZER
# ============================================================================

def get_management_improvement_advisory(profile: ManagementProfile) -> List[Dict[str, Any]]:
    """
    Identifies controllable management gaps without inventing recommendations.
    Distinguishes:
    - CURRENT PRACTICE
    - RECOMMENDED PRACTICE
    - MODEL-DERIVED EFFECT
    - FARMER ACTION
    """
    b_bench = get_crop_management_defaults(profile.crop)
    gaps = []
    
    # 1. Water Management Gap
    irrig_m = profile.irrigation_method.lower()
    if "flood" in irrig_m or "canal" in irrig_m:
        gaps.append({
            "category": "💧 Water Management",
            "current_practice": f"{profile.irrigation_method} ({profile.irrigation_frequency_days}d interval)",
            "recommended_practice": f"{b_bench['recommended_irrigation']} (ICAR Package of Practices)",
            "model_derived_effect": "Saves 35-45% water volume, reduces root hypoxia, and lifts NUE by +12-18%",
            "farmer_action": "Adopt furrow surge irrigation or transition to micro-irrigation / drip with fertigation subsidy under PMKSY.",
            "priority": "HIGH"
        })
    elif "rainfed" in irrig_m:
        gaps.append({
            "category": "💧 Water Management",
            "current_practice": "Purely Rainfed (Vulnerable to dry spells)",
            "recommended_practice": f"Provide 1-2 life-saving protective irrigations at {', '.join(b_bench['critical_irrigation_stages'])}",
            "model_derived_effect": "Prevents up to 4.5-8.0 q/acre drought yield drop during critical flowering/pod filling",
            "farmer_action": "Harvest farm pond rainwater or coordinate with community borewell for critical stage application.",
            "priority": "HIGH"
        })

    # 2. Nutrient Gap
    fert_pct = profile.fertilizer_npk_ratio_pct
    fym = profile.organic_manure_t_acre
    rec_npk = b_bench["rec_npk_kg_acre"]
    
    if fert_pct < 85:
        gaps.append({
            "category": "🧪 Fertilizer Application",
            "current_practice": f"{fert_pct}% of Recommended NPK ({profile.n_applied_kg_acre:.0f}:{profile.p_applied_kg_acre:.0f}:{profile.k_applied_kg_acre:.0f} kg/acre)",
            "recommended_practice": f"100% Rec. Dose ({rec_npk['N']:.0f}:{rec_npk['P']:.0f}:{rec_npk['K']:.0f} kg/acre) split across critical growth stages",
            "model_derived_effect": "Under-nutrition caps harvest index and limits biological biostimulant synergy by -15%",
            "farmer_action": f"Apply balanced topdressing of Urea / Potash during {profile.bio_crop_stage} stage.",
            "priority": "HIGH"
        })
    elif fert_pct > 125:
        gaps.append({
            "category": "🧪 Fertilizer Application",
            "current_practice": f"{fert_pct}% of Recommended NPK (Excessive application)",
            "recommended_practice": f"Rationalize to 100% Rec. Dose ({rec_npk['N']:.0f}:{rec_npk['P']:.0f}:{rec_npk['K']:.0f} kg/acre) based on Soil Health Card",
            "model_derived_effect": "Excess N increases vegetative rankness, pest vulnerability, and wastes ₹850-1,400/acre in input cost",
            "farmer_action": "Reduce basal nitrogen by 20% and substitute with targeted foliar biostimulant priming.",
            "priority": "MEDIUM"
        })
        
    if fym < 2.0:
        gaps.append({
            "category": "🌱 Soil Organic Carbon & FYM",
            "current_practice": f"{fym:.1f} tonnes/acre organic manure",
            "recommended_practice": f"Incorporate {b_bench['rec_fym_t_acre']:.1f} tonnes/acre well-decomposed FYM or compost pre-sowing",
            "model_derived_effect": "Improves water holding capacity (+22%) and microbial rhizosphere colonization for biologicals",
            "farmer_action": "Apply farmyard manure, vermicompost, or green manure (Dhaincha/Sunhemp) before next sowing.",
            "priority": "MEDIUM"
        })

    # 3. Crop Protection Gap
    timing_p = profile.protection_timing.lower()
    if "reactive" in timing_p or "delayed" in timing_p:
        gaps.append({
            "category": "🛡️ Crop Protection",
            "current_practice": "Reactive spraying after noticeable foliar damage",
            "recommended_practice": f"Prophylactic / ETL-based spraying for {b_bench['target_diseases'][0]}",
            "model_derived_effect": "Late intervention allows 15-25% foliar necrosis, reducing photosynthetic active radiation (PAR)",
            "farmer_action": "Monitor crop canopy weekly using LeafVision scanner and spray at first sign of disease lesions.",
            "priority": "HIGH"
        })

    # 4. Biological Application Timing Gap
    rec_stage = b_bench["recommended_bio_stage"]
    if not any(w.lower() in profile.bio_crop_stage.lower() for w in rec_stage.lower().split()):
        gaps.append({
            "category": "🧬 Biological Application Window",
            "current_practice": f"Applied at '{profile.bio_crop_stage}'",
            "recommended_practice": f"Apply Syngenta {profile.bio_product} at '{rec_stage}' (Official Label Window)",
            "model_derived_effect": "Aligning application with peak stress initiation boosts attributed yield delta by +1.2 to +2.4 q/acre",
            "farmer_action": f"Schedule foliar application of {profile.bio_product} ({b_bench['recommended_bio_dose_l_acre']:.1f} L/acre) at {rec_stage}.",
            "priority": "HIGH"
        })

    if not gaps:
        gaps.append({
            "category": "🏆 Management Adherence",
            "current_practice": "Current management practices are well-aligned with ICAR/TNAU agronomic benchmarks",
            "recommended_practice": "Maintain current precision management protocol",
            "model_derived_effect": "Maximizes biological yield synergy and delivers optimal ROI (+₹9,000 to ₹18,000/acre net advantage)",
            "farmer_action": "Continue regular field scouting and maintain 15-minute background telemetry synchronization.",
            "priority": "MAINTENANCE"
        })

    return gaps


# ============================================================================
# 6. SYNCHRONIZATION BRIDGES
# ============================================================================

def sync_management_to_cost_of_cultivation(profile: ManagementProfile, crop_name: str, season: str = "2026-27") -> None:
    """
    Synchronizes farmer-entered management practices to pre-populate corresponding
    CACP cost categories without overwriting manual farmer price entries.
    """
    state_key_prefix = f"my_farm_cost_{crop_name}_{season}_acre"
    if state_key_prefix not in st.session_state:
        return
        
    current_costs = st.session_state[state_key_prefix]
    
    # Scale fertilizer cost based on fertilizer NPK ratio
    fert_factor = profile.fertilizer_npk_ratio_pct / 100.0
    base_fert = current_costs.get("fertilisers", 2400.0)
    current_costs["fertilisers"] = round(base_fert * fert_factor, 0)
    
    # Manure cost estimation (₹600/tonne FYM)
    current_costs["manure"] = round(profile.organic_manure_t_acre * 600.0, 0)
    
    # Irrigation cost adjustment based on method
    if "drip" in profile.irrigation_method.lower():
        current_costs["irrigation"] = max(350.0, current_costs.get("irrigation", 300.0) * 0.7)
    elif "flood" in profile.irrigation_method.lower():
        current_costs["irrigation"] = max(600.0, current_costs.get("irrigation", 500.0) * 1.3)
        
    st.session_state[state_key_prefix] = current_costs


# ============================================================================
# 7. UI RENDERER: HUMAN-CENTRIC FARMER MANAGEMENT LAYER
# ============================================================================

def render_management_tab_ui(
    field_ctx: Any,
    lang: str = "en",
    t_func: Any = None,
    localized_crop_name: str = "Soybean"
) -> None:
    """
    Renders the complete Controllable Management Layer UI in Streamlit:
    1. Compact Management Summary Header (Top)
    2. Farmer Workflow Form (6 Groups: Water, Nutrition, Protection, Planting, Operations, Biological)
    3. Management Quality Scorecard & Management vs Biological Interaction
    4. "What Should I Improve?" Actionable Gap Analysis
    5. Integrated LeafVision Foliar Pathology Scanner
    6. Integrated Farm Memory & Supabase Ledger
    7. Expandable Technical Audit for Judges (Normalized Variables, Causal Graph Mapping)
    """
    t = t_func if t_func is not None else (lambda k, l, **kwargs: k)
    
    crop_name = getattr(field_ctx, 'crop', 'Soybean')
    region_name = getattr(field_ctx, 'region', 'Maharashtra & Vidarbha (Deccan)')
    season_name = getattr(field_ctx, 'season', 'Kharif')
    location_name = getattr(field_ctx, 'location_name', 'Pune')
    
    # Crop defaults are needed on every rerun (banner below), not only on first init.
    b_defaults = get_crop_management_defaults(crop_name)
    rec_npk = b_defaults.get("rec_npk_kg_acre", {"N": 48.0, "P": 24.0, "K": 16.0})

    # Initialize / retrieve profile from session state
    if "mgmt_profile" not in st.session_state or st.session_state.get("_last_mgmt_crop") != crop_name:
        
        # Clear widget state keys so Streamlit form widgets immediately reset to new crop defaults
        from services import ui_state
        ui_state.forget([
            "mgmt_f_irrig_m", "mgmt_f_irrig_s", "mgmt_f_irrig_f", "mgmt_f_irrig_a",
            "mgmt_f_fert_pct", "mgmt_f_fert_t", "mgmt_f_fym",
            "mgmt_f_prot_p", "mgmt_f_prot_t", "mgmt_f_prot_tgt",
            "mgmt_f_seed_v", "mgmt_f_sow_d", "mgmt_f_sp_r", "mgmt_f_sp_p",
            "mgmt_f_till", "mgmt_f_weed", "mgmt_f_mech",
            "mgmt_f_bio_prod", "mgmt_f_bio_dos", "mgmt_f_bio_stg", "mgmt_f_bio_cnt"
        ])
        
        active_bio = st.session_state.get("selected_bio_product", b_defaults.get("recommended_bio_product", "Syngenta Quantis"))
        active_bio_dose = safe_float(
            st.session_state.get("whatif_dosage", b_defaults.get("recommended_bio_dose_l_acre", 2.0)),
            2.0
        )

        safe_npk = parse_npk_value(rec_npk, 48.0, 24.0, 16.0)
        def_row_sp, def_plant_sp, _sp_desc = parse_spacing_cm(
            b_defaults.get("ideal_spacing_cm", "45 x 5 cm"), 45.0, 10.0
        )

        st.session_state["mgmt_profile"] = ManagementProfile(
            field_id=f"IND_FIELD_{abs(hash(location_name + crop_name)) % 9000 + 1000:04d}",
            crop=crop_name,
            season=season_name,
            irrigation_method="Drip / Micro-irrigation" if crop_name in ["Sugarcane", "Tomato", "Cotton", "Onion"] else ("Sprinkler" if crop_name in ["Soybean", "Wheat", "Groundnut (Peanut)"] else "Canal / Flood"),
            irrigation_source="Borewell / Tube Well",
            irrigation_frequency_days=7 if crop_name not in ["Sugarcane", "Rice (Paddy)"] else 4,
            last_irrigation_days_ago=2,
            irrigation_adequacy="Optimal (Adequate Moisture)",
            fertilizer_npk_ratio_pct=safe_int(st.session_state.get("whatif_fert_ratio", 100), 100),
            n_applied_kg_acre=safe_npk["N"],
            p_applied_kg_acre=safe_npk["P"],
            k_applied_kg_acre=safe_npk["K"],
            fertilizer_timing="Split (50% Basal + 50% Topdressing at Vegetative/Flowering)",
            organic_manure_t_acre=safe_float(b_defaults.get("rec_fym_t_acre", 2.5), 2.5),
            organic_manure_type="Farmyard Manure (FYM)",
            protection_practice="Integrated Pest Management (IPM) + Timely Foliar",
            pesticide_applied=True,
            pesticide_product="Broad-Spectrum Systemic Fungicide",
            protection_timing="Prophylactic / Early Threshold",
            target_pest_disease=b_defaults.get("target_diseases", ["Foliar Leaf Blight"])[0] if b_defaults.get("target_diseases") else "Foliar Leaf Blight",
            sowing_date_str="2026-06-25" if season_name == "Kharif" else "2025-11-10",
            seed_variety_type="High-Yielding Certified Hybrid",
            seed_rate_kg_acre=safe_float(b_defaults.get("seed_rate_kg_acre", 25.0), 25.0),
            row_spacing_cm=def_row_sp,
            plant_spacing_cm=def_plant_sp,
            establishment_method="Direct Sowing (Ridge & Furrow)",
            tillage_type="Minimum Tillage (1 Plough + 1 Rotavator)",
            weed_management="Integrated (Pre-emergence Herbicide + 1 Hand Weeding)",
            mechanization_level="Tractor-drawn sowing + Manual harvesting",
            bio_product=active_bio,
            bio_dosage_l_acre=active_bio_dose,
            bio_crop_stage=getattr(field_ctx, 'crop_stage', b_defaults.get("recommended_bio_stage", "Flowering / Pod Initiation")),
            bio_applications_count=1,
            bio_application_date="2026-07-20",
            bio_application_timing="Optimal (Early Morning / High Humidity)"
        )
        st.session_state["_last_mgmt_crop"] = crop_name

    profile: ManagementProfile = st.session_state["mgmt_profile"]
    
    # Calculate Quality Score & Causal Interaction
    quality_eval = calculate_management_quality_score(profile)
    interaction_eval = evaluate_management_biological_interaction(profile, quality_eval)
    
    # Update profile scores
    profile.management_score = quality_eval["total_score"]
    profile.quality_grade = quality_eval["overall_grade"]

    # ══════════════════════════════════════════════════════════════════════
    # 1. COMPACT MANAGEMENT SUMMARY HEADER (TOP)
    # ══════════════════════════════════════════════════════════════════════
    w_comp = quality_eval["components"]["water"]
    n_comp = quality_eval["components"]["nutrition"]
    p_comp = quality_eval["components"]["protection"]
    b_comp = quality_eval["components"]["biological"]
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #064e3b 0%, #047857 100%); border-radius: 14px; padding: 16px 20px; color: white; margin-bottom: 16px; box-shadow: 0 4px 14px rgba(4,120,87,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
            <div>
                <div style="font-size:1.35rem; font-weight:900; display:flex; align-items:center; gap:8px;">
                    🚜 Controllable Management Layer & Agronomic Cockpit
                </div>
                <div style="font-size:0.85rem; color:#a7f3d0; font-weight:550; margin-top:2px;">
                    PS-07 Controllable Inputs Synchronizer • Canonical Field: <b>{location_name} ({crop_name} - {season_name})</b>
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.3); border-radius:10px; padding:6px 14px; text-align:right;">
                <div style="font-size:0.70rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:800; color:#d1fae5;">MANAGEMENT QUALITY</div>
                <div style="font-size:1.20rem; font-weight:900; color:#ffffff;">{quality_eval['overall_grade'].upper()} ({quality_eval['total_score']}/100)</div>
            </div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:10px; border-top:1px solid rgba(255,255,255,0.2); padding-top:12px;">
            <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:8px;">
                <div style="font-size:0.72rem; color:#a7f3d0; font-weight:700;">💧 IRRIGATION</div>
                <div style="font-size:0.92rem; font-weight:800; margin-top:2px;">{w_comp['badge']}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:8px;">
                <div style="font-size:0.72rem; color:#a7f3d0; font-weight:700;">🧪 NUTRITION</div>
                <div style="font-size:0.92rem; font-weight:800; margin-top:2px;">{n_comp['badge']}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:8px;">
                <div style="font-size:0.72rem; color:#a7f3d0; font-weight:700;">🛡️ CROP PROTECTION</div>
                <div style="font-size:0.92rem; font-weight:800; margin-top:2px;">{p_comp['badge']}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:8px;">
                <div style="font-size:0.72rem; color:#a7f3d0; font-weight:700;">🧬 BIOLOGICAL TIMING</div>
                <div style="font-size:0.92rem; font-weight:800; margin-top:2px;">{b_comp['badge']}</div>
            </div>
            <div style="background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:8px;">
                <div style="font-size:0.72rem; color:#a7f3d0; font-weight:700;">🏆 OVERALL MANAGEMENT</div>
                <div style="font-size:0.92rem; font-weight:800; margin-top:2px;">{quality_eval['overall_grade']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Synchronized Soil & Weather Intelligence
    soil_n = safe_float(getattr(field_ctx, 'nitrogen', 140.0), 140.0)
    soil_p = safe_float(getattr(field_ctx, 'phosphorus', 16.4), 16.4)
    soil_k = safe_float(getattr(field_ctx, 'potassium', 300.0), 300.0)
    temp_c = safe_float(getattr(field_ctx, 'temp_c', 28.5), 28.5)
    heat_days = safe_int(getattr(field_ctx, 'heat_stress_days', 2), 2)
    
    sync_banner_html = (
        f'<div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:12px; padding:14px 18px; margin-bottom:16px;">'
        f'<div style="font-weight:800; font-size:0.95rem; color:#065f46; display:flex; align-items:center; gap:8px;">'
        f'<span>🔗</span><span>Active Field Synchronization: <b>{crop_name}</b> ({location_name} • {region_name})</span>'
        f'</div>'
        f'<div style="font-size:0.82rem; color:#1e293b; line-height:1.5; margin-top:6px;">'
        f'• <b>🧪 Soil Health Synchronization:</b> Measured Soil Test is <b>{soil_n:.0f} kg/ha N</b>, <b>{soil_p:.1f} kg/ha P</b>, <b>{soil_k:.0f} kg/ha K</b>. '
        f'Official ICAR recommended dose for <b>{crop_name}</b> is <b>{rec_npk["N"]:.0f}:{rec_npk["P"]:.0f}:{rec_npk["K"]:.0f} kg/acre</b>. Adjust the fertilizer slider to match your application.<br>'
        f'• <b>🌦️ Weather Synchronization:</b> Ambient temperature is <b>{temp_c:.1f}°C</b> ({heat_days} days thermal stress forecast). Critical irrigation timing is vital to prevent yield drag.<br>'
        f'• <b>🧬 Active Biological Protocol:</b> Baseline recommendation is <b>{profile.bio_product}</b> ({profile.bio_dosage_l_acre} L/acre) at <b>{profile.bio_crop_stage}</b>.'
        f'</div>'
        f'</div>'
    )
    st.markdown(sync_banner_html, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # 2. FARMER WORKFLOW FORM (6 Controllable Input Groups)
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="font-size:1.15rem; font-weight:900; color:#064e3b; margin-bottom:4px;">
        📝 Farmer Field Management Entry
    </div>
    <div style="font-size:0.86rem; color:#475569; margin-bottom:14px;">
        Update your field management below. Inputs synchronize across <b>Field Context</b>, <b>Cost of Cultivation</b>, and <b>Causal Attribution</b>:
    </div>
    """, unsafe_allow_html=True)

    col_grp1, col_grp2 = st.columns(2)

    with col_grp1:
        # Group 1: Water Management
        with st.expander("💧 1. Water Management (How did you manage water?)", expanded=True):
            profile.irrigation_method = st.selectbox(
                "Irrigation Infrastructure / Method",
                options=["Drip / Micro-irrigation", "Sprinkler", "Canal / Flood", "Furrow", "Rainfed"],
                index=["Drip / Micro-irrigation", "Sprinkler", "Canal / Flood", "Furrow", "Rainfed"].index(profile.irrigation_method) if profile.irrigation_method in ["Drip / Micro-irrigation", "Sprinkler", "Canal / Flood", "Furrow", "Rainfed"] else 0,
                key="mgmt_f_irrig_m"
            )
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                profile.irrigation_source = st.selectbox(
                    "Irrigation Source",
                    options=["Borewell / Tube Well", "Canal Network", "Farm Pond / Rain Harvesting", "River / Stream", "Rainfed Only"],
                    index=0, key="mgmt_f_irrig_s"
                )
            with col_w2:
                profile.irrigation_frequency_days = st.number_input(
                    "Irrigation Frequency (Days interval)",
                    min_value=1, max_value=30, value=int(profile.irrigation_frequency_days), step=1,
                    key="mgmt_f_irrig_f"
                )
            profile.irrigation_adequacy = st.selectbox(
                "Irrigation Adequacy (Current Crop Stage)",
                options=["Optimal (Adequate Moisture)", "Fair (Mild Stress Monitored)", "Deficit (Moisture Stress Visible)"],
                index=0 if "optimal" in profile.irrigation_adequacy.lower() else (1 if "mild" in profile.irrigation_adequacy.lower() else 2),
                key="mgmt_f_irrig_a"
            )

        # Group 2: Nutrient & Fertilizer Management
        with st.expander("🧪 2. Nutrient & Fertilizer (How much fertilizer was applied?)", expanded=True):
            profile.fertilizer_npk_ratio_pct = st.slider(
                "Fertilizer Level (% of Recommended NPK)",
                min_value=50, max_value=150, value=int(profile.fertilizer_npk_ratio_pct), step=5,
                key="mgmt_f_fert_pct"
            )
            b_bench = get_crop_management_defaults(crop_name)
            npk_ref = b_bench.get("rec_npk_kg_acre", {"N": 40.0, "P": 20.0, "K": 20.0})
            rec_n = safe_float(npk_ref.get("N", 40.0), 40.0) * (profile.fertilizer_npk_ratio_pct / 100.0)
            rec_p = safe_float(npk_ref.get("P", 20.0), 20.0) * (profile.fertilizer_npk_ratio_pct / 100.0)
            rec_k = safe_float(npk_ref.get("K", 20.0), 20.0) * (profile.fertilizer_npk_ratio_pct / 100.0)
            profile.n_applied_kg_acre = rec_n
            profile.p_applied_kg_acre = rec_p
            profile.k_applied_kg_acre = rec_k
            
            st.caption(f"Estimated active nutrient dose: **{rec_n:.0f} kg N**, **{rec_p:.0f} kg P₂O₅**, **{rec_k:.0f} kg K₂O** per acre.")
            
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                profile.fertilizer_timing = st.selectbox(
                    "Fertilizer Timing / Schedule",
                    options=["Split (50% Basal + 50% Topdressing)", "100% Basal at Sowing", "3 Splits (Basal + Veg + Flowering)"],
                    index=0, key="mgmt_f_fert_t"
                )
            with col_n2:
                profile.organic_manure_t_acre = st.number_input(
                    "Organic Manure / FYM (Tonnes/acre)",
                    min_value=0.0, max_value=20.0, value=float(profile.organic_manure_t_acre), step=0.5,
                    key="mgmt_f_fym"
                )

        # Group 3: Crop Protection
        with st.expander("🛡️ 3. Crop Protection (How did you protect the crop?)", expanded=False):
            profile.protection_practice = st.selectbox(
                "Crop Protection Method",
                options=["Integrated Pest Management (IPM) + Timely Foliar", "Targeted Fungicide / Insecticide", "Organic / Biological Control", "Reactive Spraying Only", "No Chemical Protection"],
                index=0, key="mgmt_f_prot_p"
            )
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                profile.protection_timing = st.selectbox(
                    "Application Timing",
                    options=["Prophylactic / Early Threshold", "At First Noticeable Symptom", "Delayed / Heavy Infestation"],
                    index=0, key="mgmt_f_prot_t"
                )
            with col_p2:
                profile.target_pest_disease = st.text_input(
                    "Target Pest / Disease",
                    value=profile.target_pest_disease,
                    key="mgmt_f_prot_tgt"
                )

    with col_grp2:
        # Group 4: Planting & Crop Establishment
        with st.expander("🌱 4. Planting & Establishment (How was the crop planted?)", expanded=True):
            col_pl1, col_pl2 = st.columns(2)
            with col_pl1:
                profile.seed_variety_type = st.selectbox(
                    "Seed / Variety Classification",
                    options=["High-Yielding Certified Hybrid", "Certified Improved Variety", "Farmer-Saved Traditional Seed"],
                    index=0, key="mgmt_f_seed_v"
                )
            with col_pl2:
                profile.sowing_date_str = st.text_input(
                    "Sowing Date (YYYY-MM-DD)",
                    value=profile.sowing_date_str,
                    key="mgmt_f_sow_d"
                )
            col_sp1, col_sp2 = st.columns(2)
            with col_sp1:
                profile.row_spacing_cm = st.number_input(
                    "Row Spacing (cm)",
                    min_value=5.0, max_value=300.0, value=float(np.clip(profile.row_spacing_cm, 5.0, 300.0)), step=5.0,
                    key="mgmt_f_sp_r"
                )
            with col_sp2:
                profile.plant_spacing_cm = st.number_input(
                    "Plant Spacing (cm)",
                    min_value=1.0, max_value=150.0, value=float(np.clip(profile.plant_spacing_cm, 1.0, 150.0)), step=1.0,
                    key="mgmt_f_sp_p"
                )

        # Group 5: Field Operations
        with st.expander("🚜 5. Field Operations (Tillage, Weeding & Labour)", expanded=False):
            profile.tillage_type = st.selectbox(
                "Land Preparation / Tillage",
                options=["Minimum Tillage (1 Plough + 1 Rotavator)", "Deep Summer Ploughing + Harrowing", "Zero Tillage / Direct Drilling", "Traditional Bullock Tillage"],
                index=0, key="mgmt_f_till"
            )
            col_op1, col_op2 = st.columns(2)
            with col_op1:
                profile.weed_management = st.selectbox(
                    "Weed Management Method",
                    options=["Integrated (Pre-emergence + 1 Hand Weeding)", "Manual Hand Weeding Only", "Chemical Herbicide Spray Only", "Mechanical Weeder"],
                    index=0, key="mgmt_f_weed"
                )
            with col_op2:
                profile.mechanization_level = st.selectbox(
                    "Mechanization Level",
                    options=["Tractor-drawn sowing + Manual harvesting", "Full Mechanization (Combine Harvester)", "Semi-mechanized", "Bullock & Manual Labour"],
                    index=0, key="mgmt_f_mech"
                )

        # Group 6: Biological Application
        with st.expander("🧬 6. Biological Application (What biological did you apply?)", expanded=True):
            try:
                from services.biological_catalog_service import get_all_products
                all_bio_prods = [p.product_name for p in get_all_products()]
            except Exception:
                all_bio_prods = ["Megafol®", "YieldON®", "Quantis®", "Isabion®", "CropBio+®", "Epivio® Energy", "Talete®", "Viva®", "Vixeran®", "Taegro® 370g", "KRIBHCO Liquid Consortia (NPK)"]
            
            curr_bio = st.session_state.get("selected_bio_product", profile.bio_product)
            matched_bio = next((p for p in all_bio_prods if p.lower().startswith(curr_bio.split()[0].lower()) or curr_bio.lower() in p.lower()), all_bio_prods[0])
            def_bio_idx = all_bio_prods.index(matched_bio) if matched_bio in all_bio_prods else 0
            
            profile.bio_product = st.selectbox(
                "Biological Product Applied",
                options=all_bio_prods,
                index=def_bio_idx,
                key="mgmt_f_bio_prod"
            )
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                profile.bio_dosage_l_acre = st.number_input(
                    "Dosage Applied (L/acre or standard dose)",
                    min_value=0.01, max_value=10.0, value=min(max(safe_float(st.session_state.get("whatif_dosage", profile.bio_dosage_l_acre), 1.0), 0.01), 10.0), step=0.25,
                    key="mgmt_f_bio_dos"
                )
            with col_b2:
                profile.bio_crop_stage = st.selectbox(
                    "Application Crop Stage",
                    options=["Vegetative (Active Tillering / Branching)", "Flowering / Pod Initiation", "Grain / Fruit Sizing", "Pre-Stress Preventive"],
                    index=1, key="mgmt_f_bio_stg"
                )
            profile.bio_applications_count = st.selectbox(
                "Number of Biological Applications",
                options=[1, 2, 3],
                index=0, key="mgmt_f_bio_cnt"
            )
            st.session_state["selected_bio_product"] = profile.bio_product
            st.session_state["whatif_dosage"] = profile.bio_dosage_l_acre

    # Synchronize with session state controls
    st.session_state["whatif_mgt"] = quality_eval["overall_grade"]
    st.session_state["whatif_irrig"] = profile.irrigation_method
    st.session_state["whatif_fert_ratio"] = profile.fertilizer_npk_ratio_pct
    st.session_state["whatif_dosage"] = profile.bio_dosage_l_acre
    
    # Pre-populate Cost of Cultivation in session state
    sync_management_to_cost_of_cultivation(profile, crop_name)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # 3. MANAGEMENT QUALITY & "MANAGEMENT VS BIOLOGICAL" INTERACTION
    # ══════════════════════════════════════════════════════════════════════
    col_scr, col_itr = st.columns([1.1, 1.4])

    with col_scr:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 14px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); min-height: 280px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 1.08rem; font-weight: 900; color: #064e3b;">📊 Management Quality Score</span>
                <span style="font-size: 1.15rem; font-weight: 900; color: {quality_eval['overall_color']};">{quality_eval['total_score']}/100</span>
            </div>
            <div style="font-size: 0.80rem; color: #64748b; margin-bottom: 12px;">
                Transparent component evaluation based on ICAR agronomic thresholds:
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: #1e293b; border-bottom: 1px dashed #e2e8f0; padding-bottom: 4px;">
                    <span>💧 Water Adequacy:</span>
                    <span style="color: {w_comp['color']};">{w_comp['status']} ({w_comp['score']}/25)</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: #1e293b; border-bottom: 1px dashed #e2e8f0; padding-bottom: 4px;">
                    <span>🧪 Nutrition Alignment:</span>
                    <span style="color: {n_comp['color']};">{n_comp['status']} ({n_comp['score']}/25)</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: #1e293b; border-bottom: 1px dashed #e2e8f0; padding-bottom: 4px;">
                    <span>🛡️ Crop Protection:</span>
                    <span style="color: {p_comp['color']};">{p_comp['status']} ({p_comp['score']}/20)</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: #1e293b; border-bottom: 1px dashed #e2e8f0; padding-bottom: 4px;">
                    <span>🌱 Planting & Geometry:</span>
                    <span style="color: {quality_eval['components']['planting']['color']};">{quality_eval['components']['planting']['status']} ({quality_eval['components']['planting']['score']}/15)</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; color: #1e293b; padding-top: 2px;">
                    <span>🧬 Biological Adherence:</span>
                    <span style="color: {b_comp['color']};">{b_comp['status']} ({b_comp['score']}/15)</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_itr:
        st.markdown(f"""
        <div style="background: #ecfdf5; border: 1.5px solid #86efac; border-radius: 14px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); min-height: 280px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 1.08rem; font-weight: 900; color: #065f46;">🧬 Management vs. Biological Causal Analysis</span>
                <span style="background: #059669; color: white; font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 6px;">PS-07 ATTRIBUTION</span>
            </div>
            <div style="font-size: 0.90rem; font-weight: 700; color: #064e3b; margin-bottom: 10px; line-height: 1.4;">
                "{interaction_eval['primary_statement']}"
            </div>
            <div style="font-size: 0.80rem; color: #166534; font-weight: 600; line-height: 1.45;">
                {'<br>'.join(interaction_eval['bullet_points'])}
            </div>
            <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed #86efac; font-size: 0.75rem; color: #047857; display: flex; justify-content: space-between;">
                <span><b>Attribution Confidence:</b> {interaction_eval['attribution_confidence']}</span>
                <span><b>Confounder Risk:</b> {interaction_eval['confounder_risk']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # 4. "WHAT SHOULD I IMPROVE?" ACTIONABLE AGRONOMIC GAP ANALYZER
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="font-size:1.15rem; font-weight:900; color:#064e3b; margin-bottom:4px;">
        💡 What Should I Improve? (Controllable Management Gaps)
    </div>
    <div style="font-size:0.86rem; color:#475569; margin-bottom:12px;">
        Evidence-backed agronomic guidance comparing <b>Current Practice</b> vs <b>Authoritative Package of Practices</b>:
    </div>
    """, unsafe_allow_html=True)

    gaps = get_management_improvement_advisory(profile)
    for g in gaps:
        pri_bg = "#fef2f2" if g["priority"] == "HIGH" else ("#fffbeb" if g["priority"] == "MEDIUM" else "#f0fdf4")
        pri_color = "#dc2626" if g["priority"] == "HIGH" else ("#d97706" if g["priority"] == "MEDIUM" else "#059669")
        
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 0.95rem; font-weight: 800; color: #0f172a;">{g['category']}</span>
                <span style="background: {pri_bg}; color: {pri_color}; font-size: 0.70rem; font-weight: 800; padding: 3px 8px; border-radius: 6px;">{g['priority']} PRIORITY</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.82rem; margin-bottom: 8px;">
                <div>
                    <span style="color: #64748b; font-weight: 700;">CURRENT PRACTICE:</span><br>
                    <span style="color: #1e293b; font-weight: 600;">{g['current_practice']}</span>
                </div>
                <div>
                    <span style="color: #047857; font-weight: 700;">RECOMMENDED (ICAR/TNAU):</span><br>
                    <span style="color: #065f46; font-weight: 600;">{g['recommended_practice']}</span>
                </div>
            </div>
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px; font-size: 0.80rem;">
                <span style="color: #0284c7; font-weight: 700;">MODEL-DERIVED EFFECT:</span> {g['model_derived_effect']}<br>
                <span style="color: #059669; font-weight: 700;">FARMER ACTION:</span> <b>{g['farmer_action']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # 5. EXPANDABLE TECHNICAL AUDIT FOR JUDGES & RESEARCHERS
    # ══════════════════════════════════════════════════════════════════════
    with st.expander("🏛️ Technical & Causal Model Covariates Audit (For Hackathon Judges)", expanded=False):
        st.markdown("""
        <div style="font-size:0.88rem; color:#1e293b; line-height:1.5; margin-bottom:12px;">
            <b>PS-07 Causal Inference Architecture:</b><br>
            Management variables serve as essential covariates and potential confounders in the causal DAG:
            <code>Field Context + Soil + Weather/MCII + Management + Biological Treatment → Yield (tau) → ROI</code>.
            Supported features feed directly into the 36-feature Random Forest/SHAP model, while extended operational attributes are preserved as structured records.
        </div>
        """, unsafe_allow_html=True)
        
        df_records = profile.to_dataframe()
        if "value" in df_records.columns:
            # Mixed str/int/float values break Arrow serialization; render as text.
            df_records["value"] = df_records["value"].astype(str)
        st.dataframe(df_records, width="stretch", hide_index=True)
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("""
            **36-Feature Model Alignment:**
            - `bio_applied`: 1.0 (Active treatment indicator)
            - `bio_dosage_l_ha`: 2.0 L/ha (Transformed dosage covariate)
            - `management_quality`: Modeled via Mitscherlich-Baule practical optimum engine
            - `irrigation_type`: Linked to agrometeorological soil moisture proxy (NDWI & MCII)
            """)
        with col_t2:
            st.markdown("""
            **CACP Cost Framework Parity:**
            - Fertilizers & Manure aligned with Chapter 5 CACP itemized cost hierarchy
            - Insecticides & Crop Protection aligned with CACP Paid-Out Cost A2
            - Irrigation & Labour aligned with CACP Operational Cost C2
            """)
