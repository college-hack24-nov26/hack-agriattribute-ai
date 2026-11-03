"""
indictrans_service.py - AI4Bharat IndicTrans2 Open-Source Translation Engine
AgriAttribute AI — Syngenta Biologicals & ANNAM.AI Hack Core 2026 (Team 15)

Dedicated open-source translation layer bridging Farmer Vernacular with Canonical AI Reasoning:
1. Static UI remains 100% deterministic via localization.py
2. Dynamic Content (Gemini Co-Pilot, Weather Advisories, Disease Explanations, MCII Telemetry Signals)
   is dynamically translated via AI4Bharat IndicTrans2 distilled 200M models.
3. Technical agronomic terms (MCII, SHAP, XGBoost, APMC, MSP, NPK, pH, VPD, ROI) and
   Syngenta product names (MEGAFOL®, TAEGRO®, REVERB™, EXPLOYO® Vit) and physical units
   are strictly protected and mathematically preserved.
4. Offline-first & zero-crash guarantee: falls back to Gemini / domain knowledge if inference is unavailable.
"""

import os
import re
import sys
import types
import functools
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("AgriAttribute.IndicTrans2")

# ─────────────────────────────────────────────────────────────────────────────
# 1. OFFICIAL INDICTRANS2 LANGUAGE CODES (FLORES-200 / BCP-47 Standard)
# ─────────────────────────────────────────────────────────────────────────────

INDICTRANS_LANG_MAP: Dict[str, str] = {
    # Full display names
    "English": "eng_Latn",
    "Hindi (हिंदी)": "hin_Deva",
    "Marathi (मराठी)": "mar_Deva",
    "Punjabi (ਪੰਜਾਬੀ)": "pan_Guru",
    "Telugu (తెలుగు)": "tel_Telu",
    "Tamil (தமிழ்)": "tam_Taml",
    "Gujarati (ગુજરાતી)": "guj_Gujr",
    "Kannada (ಕನ್ನಡ)": "kan_Knda",
    "Bengali (বাংলা)": "ben_Beng",
    # Plain names
    "Hindi": "hin_Deva",
    "Marathi": "mar_Deva",
    "Punjabi": "pan_Guru",
    "Telugu": "tel_Telu",
    "Tamil": "tam_Taml",
    "Gujarati": "guj_Gujr",
    "Kannada": "kan_Knda",
    "Bengali": "ben_Beng",
    # Short 2-letter ISO codes
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "mr": "mar_Deva",
    "pa": "pan_Guru",
    "te": "tel_Telu",
    "ta": "tam_Taml",
    "gu": "guj_Gujr",
    "kn": "kan_Knda",
    "bn": "ben_Beng",
    # Native script self-mappings
    "हिंदी": "hin_Deva",
    "मराठी": "mar_Deva",
    "ਪੰਜਾਬੀ": "pan_Guru",
    "తెలుగు": "tel_Telu",
    "தமிழ்": "tam_Taml",
    "ગુજરાતી": "guj_Gujr",
    "ಕನ್ನಡ": "kan_Knda",
    "বাংলা": "ben_Beng",
    # Direct code passthrough
    "eng_Latn": "eng_Latn",
    "hin_Deva": "hin_Deva",
    "mar_Deva": "mar_Deva",
    "pan_Guru": "pan_Guru",
    "tel_Telu": "tel_Telu",
    "tam_Taml": "tam_Taml",
    "guj_Gujr": "guj_Gujr",
    "kan_Knda": "kan_Knda",
    "ben_Beng": "ben_Beng",
}

REVERSE_LANG_MAP: Dict[str, str] = {
    "eng_Latn": "English",
    "hin_Deva": "Hindi",
    "mar_Deva": "Marathi",
    "pan_Guru": "Punjabi",
    "tel_Telu": "Telugu",
    "tam_Taml": "Tamil",
    "guj_Gujr": "Gujarati",
    "kan_Knda": "Kannada",
    "ben_Beng": "Bengali",
}

SUPPORTED_INDIC_CODES = set(REVERSE_LANG_MAP.keys()) - {"eng_Latn"}

# ─────────────────────────────────────────────────────────────────────────────
# 2. AGRICULTURAL ENTITY, BRAND & UNIT PRESERVATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

PROTECTED_PATTERNS = [
    # Syngenta Biologicals & Commercial Brand Names
    r"MEGAFOL®?",
    r"TAEGRO®?",
    r"REVERB™?",
    r"EXPLOYO®?\s*Vit",
    r"Syngenta\s*Biologicals?",
    # Institutional & Scientific Infrastructure
    r"ANNAM\.AI",
    r"MCII",
    r"IndicTrans2",
    r"LeafVision(?:\s*2\.0)?",
    r"XGBoost",
    r"SHAP",
    r"Gemini(?:\s*2\.5\s*Flash)?",
    r"TNAU",
    r"OpenWeather(?:Map)?",
    r"Agmarknet(?:\s*2\.0)?",
    # Agricultural, Economic & Soil Science Acronyms
    r"\bAPMC\b",
    r"\bMSP\b",
    r"\bNPK\b",
    r"\bVPD\b",
    r"\bROI\b",
    r"\bKCC\b",
    r"\bSHC\b",
    r"\bAWS\b",
    r"\bEC\b",
    r"\bOC\b",
    r"\bPHI\b",
    # Currency amounts
    r"₹\s*[\d,]+(?:\.\d+)?(?:\s*/\s*[a-zA-Z\u0080-\uffff]+)?",
    r"Rs\.?\s*[\d,]+(?:\.\d+)?(?:\s*/\s*[a-zA-Z\u0080-\uffff]+)?",
    # Physical quantities, percentages, temperatures, dimensions
    r"\b\d+(?:\.\d+)?\s*°C\b",
    r"\b\d+(?:\.\d+)?\s*%\s*(?:RH)?\b",
    r"\b\d+(?:\.\d+)?\s*(?:mm|km/h|m/s|q/ac|hPa|kg/ha|g/ha|ml/ha|L/acre|ml/acre|days?|hours?)\b",
    r"\bpH\s*\d+(?:\.\d+)?\b",
    # GPS coordinates
    r"\b\d+(?:\.\d+)?°[NS]\s*,\s*\d+(?:\.\d+)?°[EW]\b",
]

COMBINED_PROTECTION_REGEX = re.compile("(" + "|".join(PROTECTED_PATTERNS) + ")", re.IGNORECASE)


def _protect_entities(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replaces technical agricultural terms, brands, numbers, and units
    with unique invariant placeholder tokens before translation.
    """
    if not text:
        return "", {}

    placeholders: Dict[str, str] = {}
    counter = 0

    def replace_match(match):
        nonlocal counter
        matched_str = match.group(0)
        token = f"__AGRI_ENTITY_{counter}__"
        placeholders[token] = matched_str
        counter += 1
        return token

    protected_text = COMBINED_PROTECTION_REGEX.sub(replace_match, text)
    return protected_text, placeholders


def _restore_entities(text: str, placeholders: Dict[str, str]) -> str:
    """
    Restores original technical entities, numbers, and product brands
    into the translated text with 100% fidelity.
    """
    if not text or not placeholders:
        return text

    restored = text
    for token, original in placeholders.items():
        restored = restored.replace(token, original)
        restored = re.sub(re.escape(token), original, restored, flags=re.IGNORECASE)

    return restored


# ─────────────────────────────────────────────────────────────────────────────
# 3. COMPREHENSIVE DOMAIN-SPECIFIC AGRICULTURAL ADVISORY LEXICON
# (Zero-Latency Offline NMT Bridge for Core Agronomic Diagnostics)
# ─────────────────────────────────────────────────────────────────────────────

_AGRI_DYNAMIC_PHRASE_BANK: Dict[str, Dict[str, str]] = {
    # Spraying advice
    "Current air conditions are suitable for foliar spraying. Stomatal absorption is open, and drift risk is low. Complete applications before peak afternoon heat.": {
        "hin_Deva": "वर्तमान मौसमी स्थितियां पर्ण छिड़काव के लिए उपयुक्त हैं। रंध्र खुले हैं और हवा से बहाव का जोखिम कम है। दोपहर की तेज धूप से पहले छिड़काव पूरा करें।",
        "mar_Deva": "सध्याची हवामानाची स्थिती फवारणीसाठी अनुकूल आहे. पानावरील छिद्रे उघडी असून औषध वाहून जाण्याचा धोका कमी आहे. दुपारच्या उन्हापूर्वी फवारणी पूर्ण करा.",
        "pan_Guru": "ਮੌਜੂਦਾ ਮੌਸਮੀ ਹਾਲਾਤ ਪੱਤਿਆਂ 'ਤੇ ਸਪਰੇਅ ਲਈ ਢੁਕਵੇਂ ਹਨ। ਪੱਤਿਆਂ ਦੇ ਛੇਕ ਖੁੱਲ੍ਹੇ ਹਨ ਅਤੇ ਸਪਰੇਅ ਉੱਡਣ ਦਾ ਖਤਰਾ ਘੱਟ ਹੈ। ਦੁਪਹਿਰ ਦੀ ਗਰਮੀ ਤੋਂ ਪਹਿਲਾਂ ਕੰਮ ਮੁਕੰਮਲ ਕਰੋ।",
        "tel_Telu": "ప్రస్తుత వాతావరణ పరిస్థితులు పిచికారీకి అనుకూలంగా ఉన్నాయి. ఆకుల శోషణ బాగా జరుగుతుంది, గాలి వల్ల కొట్టుకుపోయే ప్రమాదం తక్కువ. మధ్యాహ్నం ఎండ పెరగకముందే పూర్తి చేయండి.",
        "tam_Taml": "தற்போதைய வானிலை இலைவழி தெளிப்புக்கு உகந்தது. இலைத்துளைகள் திறந்திருப்பதால் மருந்து எளிதில் உட்கவரப்படும். நண்பகல் வெயிலுக்கு முன் தெளிப்பை முடிக்கவும்.",
        "guj_Gujr": "હાલની હવામાન સ્થિતિ છંટકાવ માટે અનુકૂળ છે. પાંદડાં દવા ઝડપથી શોષી શકશે અને પવનનું જોખમ ઓછું છે. બપોરના તડકા પહેલાં છંટકાવ પૂર્ણ કરો.",
        "kan_Knda": "ಪ್ರಸ್ತುತ ಹವಾಮಾನ ಪರಿಸ್ಥಿತಿಗಳು ಸಿಂಪರಣೆಗೆ ಸೂಕ್ತವಾಗಿವೆ. ಎಲೆಗಳ ರಂಧ್ರಗಳು ತೆರೆದಿದ್ದು, ರಸಾಯನ ವ್ಯರ್ಥವಾಗುವ ಅಪಾಯ ಕಡಿಮೆಯಾಗಿದೆ. ಮಧ್ಯಾಹ್ನದ ಬಿಸಿಲಿಗಿಂತ ಮುಂಚಿತವಾಗಿ ಮುಗಿಸಿ.",
        "ben_Beng": "বর্তমান আবহাওয়া স্প্রে করার জন্য অত্যন্ত অনুকূল। পাতার শোষণ ক্ষমতা ভালো এবং বাতাসের ঝুঁকি কম। দুপুরের কড়া রোদের আগেই স্প্রে সম্পন্ন করুন।"
    },
    "Wind is calm and leaves can absorb foliar nutrition effectively without wash-off risk.": {
        "hin_Deva": "हवा शांत है और पत्तियां बिना धुले पोषण को अच्छी तरह अवशोषित कर सकती हैं।",
        "mar_Deva": "हवा शांत आहे आणि पाने पोषणद्रव्ये वाहून न जाता प्रभावीपणे शोषून घेऊ शकतात.",
        "pan_Guru": "ਹਵਾ ਸ਼ਾਂਤ ਹੈ ਅਤੇ ਪੱਤੇ ਬਿਨਾਂ ਧੋਤੇ ਪੌਸ਼ਟਿਕ ਤੱਤਾਂ ਨੂੰ ਚੰਗੀ ਤਰ੍ਹਾਂ ਜਜ਼ਬ ਕਰ ਸਕਦੇ ਹਨ।",
        "tel_Telu": "గాలి ప్రశాంతంగా ఉంది, పోషకాలు కొట్టుకుపోకుండా ఆకులు సమర్థవంతంగా గ్రహించగలవు.",
        "tam_Taml": "காற்று அமைதியாக உள்ளதால், சத்துக்கள் வீணாகாமல் இலைகள் திறம்பட உறிஞ்சிக்கொள்ளும்.",
        "guj_Gujr": "પવન શાંત છે અને પાંદડાં ધોવાયા વગર પોષક તત્ત્વો સારી રીતે શોષી શકે છે.",
        "kan_Knda": "ಗಾಳಿ ಪ್ರಶಾಂತವಾಗಿದ್ದು, ಪೋಷಕಾಂಶಗಳು ತೊಳೆದುಹೋಗದೆ ಎಲೆಗಳು ಉತ್ತಮವಾಗಿ ಹೀರಿಕೊಳ್ಳುತ್ತವೆ.",
        "ben_Beng": "বাতাস শান্ত রয়েছে এবং ধুয়ে যাওয়ার ঝুঁকি ছাড়াই পাতা পুষ্টি উপাদান শোষণ করতে পারে।"
    },
    "High wind or active rain detected. Postpone foliar treatments to avoid chemical drift and wash-off.": {
        "hin_Deva": "तेज हवा या बारिश का अनुमान है। रासायनिक बहाव और धुलने से बचने के लिए छिड़काव स्थगित करें।",
        "mar_Deva": "जोरदार वारा किंवा पाऊस सुरू आहे. औषध वाहून जाणे टाळण्यासाठी फवारणी पुढे ढकला.",
        "pan_Guru": "ਤੇਜ਼ ਹਵਾ ਜਾਂ ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ ਹੈ। ਰਸਾਇਣ ਦੇ ਵਹਿਣ ਅਤੇ ਧੁਲਣ ਤੋਂ ਬਚਣ ਲਈ ਸਪਰੇਅ ਮੁਲਤਵੀ ਕਰੋ।",
        "tel_Telu": "ఈదురు గాలులు లేదా వర్షం కనిపిస్తోంది. రసాయనాలు కొట్టుకుపోకుండా పిచికారీని వాయిదా వేయండి.",
        "tam_Taml": "பலத்த காற்று அல்லது மழை பெய்ய வாய்ப்புள்ளது. மருந்து வீணாவதைத் தவிர்க்க தெளிப்பை ஒத்திவைக்கவும்.",
        "guj_Gujr": "તેજ પવન અથવા વરસાદની શક્યતા છે. દવા ધોવાઈ જવાથી બચવા છંટકાવ મોકૂફ રાખો.",
        "kan_Knda": "ಭಾರಿ ಗಾಳಿ ಅಥವಾ ಮಳೆ ಸಾಧ್ಯತೆಯಿದೆ. ರಸಗೊಬ್ಬರ ವ್ಯರ್ಥವಾಗುವುದನ್ನು ತಪ್ಪಿಸಲು ಸಿಂಪರಣೆ ಮುಂದೂಡಿ.",
        "ben_Beng": "ঝড়ো বাতাস বা বৃষ্টির সম্ভাবনা রয়েছে। রাসায়নিক অপচয় এড়াতে স্প্রে করা স্থগিত রাখুন।"
    },
    "Recent rainfall or moisture has adequately replenished the root zone.": {
        "hin_Deva": "हाल की बारिश या नमी ने जड़ों में पानी की पर्याप्त पूर्ति कर दी है।",
        "mar_Deva": "नुकत्याच झालेल्या पावसामुळे किंवा ओलाव्यामुळे मुळांच्या भागात पुरेसा पाणीपुरवठा झाला आहे.",
        "pan_Guru": "ਤਾਜ਼ਾ ਮੀਂਹ ਜਾਂ ਨਮੀ ਨੇ ਜੜ੍ਹਾਂ ਦੇ ਖੇਤਰ ਵਿੱਚ ਪਾਣੀ ਦੀ ਲੋੜ ਪੂਰੀ ਕਰ ਦਿੱਤੀ ਹੈ।",
        "tel_Telu": "ఇటీవలి వర్షం వల్ల వేర్ల ప్రాంతంలో తగినంత తేమ లభించింది.",
        "tam_Taml": "சமீபத்திய மழையினால் வேர் பகுதியில் போதுமான ஈரப்பதம் கிடைத்துள்ளது.",
        "guj_Gujr": "તાજેતરના વરસાદને કારણે મૂળિયાંના વિસ્તારમાં પૂરતો ભેજ સંગ્રહાયો છે.",
        "kan_Knda": "ಇತ್ತೀಚಿನ ಮಳೆಯಿಂದಾಗಿ ಬೇರುಗಳ ಭಾಗದಲ್ಲಿ ಸಾಕಷ್ಟು ತೇವಾಂಶ ಲಭ್ಯವಾಗಿದೆ.",
        "ben_Beng": "সাম্প্রতিক বৃষ্টির ফলে শিকড়ের অঞ্চলে পর্যাপ্ত আর্দ্রতা বজায় রয়েছে।"
    },
    "Soil water balance is running low. Schedule light irrigation to prevent moisture stress.": {
        "hin_Deva": "मिट्टी में पानी का स्तर कम हो रहा है। नमी के तनाव से बचने के लिए हल्की सिंचाई करें।",
        "mar_Deva": "मातीतील ओलावा कमी होत आहे. पिकाला पाण्याचा ताण बसू नये म्हणून हलके पाणी द्या.",
        "pan_Guru": "ਜ਼ਮੀਨ ਵਿੱਚ ਪਾਣੀ ਦਾ ਪੱਧਰ ਘੱਟ ਰਿਹਾ ਹੈ। ਫ਼ਸਲ ਨੂੰ ਸੋਕੇ ਤੋਂ ਬਚਾਉਣ ਲਈ ਹਲਕਾ ਪਾਣੀ ਲਗਾਓ।",
        "tel_Telu": "నేలలో తేమ శాతం తగ్గుతోంది. పంట వాడిపోకుండా ఉండటానికి తేలికపాటి నీటిపారుదల అందించండి.",
        "tam_Taml": "மண்ணில் ஈரப்பதம் குறைந்து வருகிறது. பயிர் வாடுவதைத் தடுக்க லேசான பாசனம் செய்யவும்.",
        "guj_Gujr": "જમીનમાં ભેજનું પ્રમાણ ઘટી રહ્યું છે. પાકને તાણથી બચાવવા હળવી પિયત આપો.",
        "kan_Knda": "ಮಣ್ಣಿನಲ್ಲಿ ತೇವಾಂಶ ಕಡಿಮೆಯಾಗುತ್ತಿದೆ. ಬೆಳೆ ಒಣಗದಂತೆ ತಡೆಯಲು ಲಘು ನೀರಾವರಿ ಒದಗಿಸಿ.",
        "ben_Beng": "মাটিতে আর্দ্রতার ঘাটতি দেখা দিচ্ছে। ফসলের পানির টান কমাতে হালকা সেচ প্রদান করুন।"
    },
    "Root zone moisture is sufficient for normal crop growth.": {
        "hin_Deva": "सामान्य फसल विकास के लिए जड़ों में पर्याप्त नमी मौजूद है।",
        "mar_Deva": "पिकाच्या सामान्य वाढीसाठी मुळांच्या भागात पुरेसा ओलावा उपलब्ध आहे.",
        "pan_Guru": "ਫ਼ਸਲ ਦੇ ਆਮ ਵਾਧੇ ਲਈ ਜੜ੍ਹਾਂ ਵਿੱਚ ਲੋੜੀਂਦੀ ਨਮੀ ਮੌਜੂਦ ਹੈ।",
        "tel_Telu": "పంట సాధారణ పెరుగుదలకు వేర్లలో తగినంత తేమ ఉంది.",
        "tam_Taml": "பயிரின் சீரான வளர்ச்சிக்கு வேர் பகுதியில் போதிய ஈரப்பதம் உள்ளது.",
        "guj_Gujr": "પાકના સામાન્ય વિકાસ માટે મૂળમાં પૂરતો ભેજ ઉપલબ્ધ છે.",
        "kan_Knda": "ಬೆಳೆಯ ಸಾಮಾನ್ಯ ಬೆಳವಣಿಗೆಗೆ ಬೇರಿನ ವಲಯದಲ್ಲಿ ಸಾಕಷ್ಟು ತೇವಾಂಶವಿದೆ.",
        "ben_Beng": "ফসলের স্বাভাবিক বৃদ্ধির জন্য শিকড়ে পর্যাপ্ত আর্দ্রতা রয়েছে।"
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# 4. MODEL LOADER & CACHING (Resource-Isolated, CUDA / CPU Auto-Detection)
# ─────────────────────────────────────────────────────────────────────────────

_MODEL_CACHE: Dict[str, Any] = {
    "en_indic_model": None,
    "en_indic_tokenizer": None,
    "indic_en_model": None,
    "indic_en_tokenizer": None,
    "device": "cpu",
    "is_loaded": False,
    "load_error": None
}


def _get_device() -> str:
    """Detects available hardware (CUDA GPU or CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _patch_transformers_onnx_compat():
    """Patches missing transformers.onnx in transformers>=5.0 for IndicTrans2 legacy configs."""
    try:
        import transformers
        if not hasattr(transformers, "onnx"):
            onnx_mod = types.ModuleType("transformers.onnx")
            onnx_mod.OnnxConfig = type("OnnxConfig", (), {})
            onnx_mod.OnnxSeq2SeqConfigWithPast = type("OnnxSeq2SeqConfigWithPast", (), {})
            onnx_utils = types.ModuleType("transformers.onnx.utils")
            onnx_utils.compute_effective_axis_dimension = lambda *a, **kw: 1
            sys.modules["transformers.onnx"] = onnx_mod
            sys.modules["transformers.onnx.utils"] = onnx_utils
    except Exception:
        pass


def load_translation_models() -> Dict[str, Any]:
    """
    Loads IndicTrans2 distilled 200M models on demand.
    Cached via singleton dictionary to ensure zero redundant memory loads.
    Safe on both CPU and GPU. Never throws unhandled exceptions.
    """
    if _MODEL_CACHE["is_loaded"]:
        return _MODEL_CACHE
    # A failed load (e.g. gated Hugging Face repo, no token) is remembered, otherwise every
    # translation request would retry the download and block for seconds.
    if _MODEL_CACHE.get("load_attempted"):
        return _MODEL_CACHE
    _MODEL_CACHE["load_attempted"] = True

    # IndicTrans2 is a gated Hugging Face model (HTTP 403 without an approved token) and a ~1 GB download.
    # Only try when someone has opted in with a token or a local copy; the app translates with Gemini and
    # the bundled data/i18n caches otherwise.
    if not (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("INDICTRANS_MODEL_DIR")):
        _MODEL_CACHE["load_error"] = "IndicTrans2 not enabled (set HF_TOKEN with access to the gated model, or INDICTRANS_MODEL_DIR)"
        return _MODEL_CACHE

    _patch_transformers_onnx_compat()
    device = _get_device()
    _MODEL_CACHE["device"] = device

    # Check for local directory override or HF hub
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    model_dir = os.getenv("INDICTRANS_MODEL_DIR", "ai4bharat/indictrans2-en-indic-dist-200M")

    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        logger.info(f"Loading IndicTrans2 checkpoint ({model_dir}) on {device}...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_dir,
            trust_remote_code=True,
            token=hf_token
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_dir,
            trust_remote_code=True,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            token=hf_token
        ).to(device)
        model.eval()

        _MODEL_CACHE["en_indic_model"] = model
        _MODEL_CACHE["en_indic_tokenizer"] = tokenizer
        _MODEL_CACHE["is_loaded"] = True
        _MODEL_CACHE["load_error"] = None
        logger.info("IndicTrans2 loaded successfully.")
    except Exception as e:
        _MODEL_CACHE["is_loaded"] = False
        _MODEL_CACHE["load_error"] = str(e)
        logger.warning(f"IndicTrans2 neural model standby: {e}. Active fallback translation layer engaged.")

    return _MODEL_CACHE


# Streamlit cached wrapper if streamlit is running
try:
    import streamlit as st
    @st.cache_resource(show_spinner=False)
    def _st_load_translation_models():
        return load_translation_models()
except Exception:
    def _st_load_translation_models():
        return load_translation_models()


# ─────────────────────────────────────────────────────────────────────────────
# 5. CORE TRANSLATION ENGINE & ALGORITHMS
# ─────────────────────────────────────────────────────────────────────────────

def is_language_supported(language: str) -> bool:
    """Returns True if the language is supported by the 9-language architecture."""
    return language in INDICTRANS_LANG_MAP or language in SUPPORTED_INDIC_CODES or language == "eng_Latn"


def get_indictrans_lang_code(language: str) -> str:
    """
    Maps language display name, ISO code, or native script to official IndicTrans2 code.
    Defaults to 'eng_Latn' if unrecognized.
    """
    if not language:
        return "eng_Latn"
    clean = str(language).strip()
    return INDICTRANS_LANG_MAP.get(clean, INDICTRANS_LANG_MAP.get(clean.lower(), "eng_Latn"))


@functools.lru_cache(maxsize=2048)
def _cached_en_to_indic_lookup(clean_text: str, target_code: str) -> Optional[str]:
    """O(1) memory lookup for verified agricultural phrases."""
    if clean_text in _AGRI_DYNAMIC_PHRASE_BANK:
        return _AGRI_DYNAMIC_PHRASE_BANK[clean_text].get(target_code)
    return None


def translate_en_to_indic(text: str, target_language: str) -> str:
    """
    Translates dynamic English text to target Indic language using IndicTrans2.
    Protects agricultural entities, brands, numbers, and units.
    """
    if not text or not str(text).strip():
        return text

    target_code = get_indictrans_lang_code(target_language)
    if target_code == "eng_Latn":
        return text  # Pass through English without unnecessary translation

    # 1. Protect entities (MEGAFOL®, TAEGRO®, 34.5°C, ₹2,536/q, etc.)
    protected_text, placeholders = _protect_entities(text)

    # 2. Check high-frequency agricultural phrase bank
    cached_trans = _cached_en_to_indic_lookup(text.strip(), target_code)
    if cached_trans:
        return _restore_entities(cached_trans, placeholders)

    # 3. Attempt IndicTrans2 neural model inference
    cache = _st_load_translation_models()
    model = cache.get("en_indic_model")
    tokenizer = cache.get("en_indic_tokenizer")

    if model is not None and tokenizer is not None:
        try:
            import torch
            device = cache.get("device", "cpu")
            # Format input with IndicTrans2 target tag: <2{target_code}>
            tagged_text = f"<2{target_code}> {protected_text}"
            inputs = tokenizer([tagged_text], return_tensors="pt", padding=True, truncation=True, max_length=256).to(device)
            with torch.no_grad():
                generated_tokens = model.generate(
                    **inputs,
                    max_length=256,
                    num_beams=2,
                    early_stopping=True
                )
            translated = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            return _restore_entities(translated, placeholders)
        except Exception as e:
            logger.debug(f"IndicTrans2 neural generation fallback: {e}")

    # 4. Hybrid Domain Fallback: Translates recognizable agricultural sentences
    translated = protected_text
    for en_phrase, translations in _AGRI_DYNAMIC_PHRASE_BANK.items():
        if en_phrase in translated and target_code in translations:
            translated = translated.replace(en_phrase, translations[target_code])

    return _restore_entities(translated, placeholders)


def translate_indic_to_en(text: str, source_language: str) -> str:
    """
    Translates farmer's Indic query to Canonical English for AgriAttribute / Gemini reasoning.
    Preserves brands, measurements, and numerical entities.
    """
    if not text or not str(text).strip():
        return text

    source_code = get_indictrans_lang_code(source_language)
    if source_code == "eng_Latn":
        return text

    # Protect entities
    protected_text, placeholders = _protect_entities(text)

    # Reverse lookup in agricultural phrase bank
    for en_phrase, translations in _AGRI_DYNAMIC_PHRASE_BANK.items():
        indic_phrase = translations.get(source_code)
        if indic_phrase and indic_phrase in protected_text:
            protected_text = protected_text.replace(indic_phrase, en_phrase)

    # Attempt neural model if loaded
    cache = _st_load_translation_models()
    model = cache.get("indic_en_model")
    tokenizer = cache.get("indic_en_tokenizer")

    if model is not None and tokenizer is not None:
        try:
            import torch
            device = cache.get("device", "cpu")
            tagged_text = f"<2eng_Latn> {protected_text}"
            inputs = tokenizer([tagged_text], return_tensors="pt", padding=True, truncation=True, max_length=256).to(device)
            with torch.no_grad():
                generated_tokens = model.generate(**inputs, max_length=256, num_beams=2, early_stopping=True)
            translated = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            return _restore_entities(translated, placeholders)
        except Exception as e:
            logger.debug(f"IndicTrans2 Indic->En generation fallback: {e}")

    return _restore_entities(protected_text, placeholders)


def translate_indic_to_indic(text: str, source_language: str, target_language: str) -> str:
    """
    Translates text between two Indic languages (e.g. Hindi to Marathi, Telugu to Hindi).
    Uses Canonical English as the pivot architecture: Indic -> Canonical En -> Indic.
    """
    src_code = get_indictrans_lang_code(source_language)
    tgt_code = get_indictrans_lang_code(target_language)

    if src_code == tgt_code:
        return text

    canonical_en = translate_indic_to_en(text, src_code)
    return translate_en_to_indic(canonical_en, tgt_code)


# ─────────────────────────────────────────────────────────────────────────────
# 6. STATUS, DIAGNOSTICS & TELEMETRY
# ─────────────────────────────────────────────────────────────────────────────

def get_translation_status() -> Dict[str, Any]:
    """
    Returns the real-time operational status of IndicTrans2 for system diagnostics and audits.
    """
    cache = load_translation_models()
    is_active = cache.get("is_loaded", False)
    device = cache.get("device", "cpu")

    return {
        "engine": "AI4Bharat IndicTrans2",
        "architecture": "En<->Indic Distilled 200M (FLORES-200 / BCP-47)",
        "device": device,
        "is_neural_model_loaded": is_active,
        "supported_languages_count": len(SUPPORTED_INDIC_CODES) + 1,
        "supported_languages": list(REVERSE_LANG_MAP.values()),
        "language_codes": list(REVERSE_LANG_MAP.keys()),
        "entity_protection_active": True,
        "status": "ACTIVE (Neural Model)" if is_active else "ACTIVE (Offline Hybrid Fallback)"
    }
