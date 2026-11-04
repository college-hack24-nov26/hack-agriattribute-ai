"""
gemini_service.py - Google Gemini 2.5 Flash Multimodal AI Engine + Multilingual Voice I/O
AgriAttribute AI — Syngenta Biologicals & ANNAM.AI Hack Core 2026 (Team 15)

Precision Conversational Agronomist & Field Intelligence Co-Pilot:
Natively processes Voice Notes (audio), Field Images (leaf/crop/pest), and Text Queries,
deeply synchronized with all platform modules:
1. Live Weather (OpenWeatherMap + Meteoblue)
2. Soil Health Card (DAC&FW 12-parameter standards)
3. LeafVision 2.0 Foliar Telemetry
4. Agmarknet 2.0 Live Mandi Pulse
5. Counterfactual Biological ROI & Yield Attribution
"""

import os
import requests
import base64
import html as html_mod
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from services.management_engine import safe_float, safe_int
except (ImportError, ModuleNotFoundError):
    from management_engine import safe_float, safe_int

def _clean_gemini_key(k: str) -> str:
    if not k or not isinstance(k, str):
        return ""
    k = k.strip()
    if k.startswith("your_") or len(k) < 20:
        return ""
    return k

def _get_gemini_key() -> str:
    val = os.getenv("GEMINI_API_KEY", "")
    if not val:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                val = str(st.secrets["GEMINI_API_KEY"])
        except Exception:
            pass
    return _clean_gemini_key(val)


# ---------------------------------------------------------------------------
# One caller for every Gemini request, with automatic model fallback.
# The free tier runs out per model (HTTP 429) and busy models return 503, so each request walks a short
# list of models and skips the ones that recently failed. Override the list with GEMINI_MODELS.
# ---------------------------------------------------------------------------
import time as _time
import copy as _copy

GEMINI_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_MODELS", "gemini-2.5-flash,gemini-3.5-flash-lite,gemini-flash-lite-latest,gemini-3.1-flash-lite"
).split(",") if m.strip()]
_MODEL_COOLDOWN = {}


def _for_model(payload: dict, model: str) -> dict:
    """thinkingConfig.thinkingBudget is a Gemini 2.5 setting; newer lite models reject it."""
    if model.startswith("gemini-2.5"):
        return payload
    body = _copy.deepcopy(payload)
    body.get("generationConfig", {}).pop("thinkingConfig", None)
    return body


def generate_content(payload: dict, timeout: float = 30.0, wait_s: float = 0.0):
    """
    POST generateContent on the first model that answers. Returns (response_json, model) or (None, None).
    wait_s > 0 (offline jobs only) waits for a per-minute limit to clear instead of giving up.
    """
    key = _get_gemini_key()
    if not key:
        return None, None
    deadline = _time.time() + wait_s
    while True:
        for model in GEMINI_MODELS:
            now = _time.time()
            if _MODEL_COOLDOWN.get(model, 0) > now:
                continue
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                  json=_for_model(payload, model), timeout=timeout,
                                  headers={"Content-Type": "application/json", "x-goog-api-key": key})
            except requests.RequestException:
                _MODEL_COOLDOWN[model] = now + 30
                continue
            if r.status_code == 200:
                return r.json(), model
            if r.status_code == 429:
                # per-day quota: park the model; per-minute limit: a short pause is enough
                _MODEL_COOLDOWN[model] = now + (3600 if "PerDay" in r.text else 30)
            elif r.status_code == 404:
                _MODEL_COOLDOWN[model] = now + 86400    # retired model
            elif r.status_code >= 500:
                _MODEL_COOLDOWN[model] = now + 45       # busy
            elif r.status_code in (401, 403):
                return None, None                       # key problem: no model will work
        soonest = min((_MODEL_COOLDOWN.get(m, 0) for m in GEMINI_MODELS), default=0)
        if _time.time() >= deadline or soonest > deadline:
            return None, None
        _time.sleep(max(1.0, soonest - _time.time()))


def response_text(data) -> str:
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def model_label(model) -> str:
    return f"Google {model.replace('gemini-', 'Gemini ').replace('-', ' ').title()} API" if model else "Gemini"


def _translation_engine_label() -> str:
    """Name of the translation layer that is actually active (IndicTrans2 is a gated model)."""
    try:
        from services import indictrans_service as _it
        # Read the cache only: get_translation_status() would trigger a heavy model load.
        if _it._MODEL_CACHE.get("is_loaded"):
            return "AI4Bharat IndicTrans2 (Distilled 200M)"
    except Exception:
        pass
    return "Gemini multilingual + glossary fallback (IndicTrans2 not loaded)"

# ─── System Prompt ────────────────────────────────────────────────────────────
AGRI_SYSTEM_PROMPT = """
You are AgriAttribute AI — a precision agronomic advisory assistant built for Indian farmers, agricultural extension workers, and field officers (Syngenta & ANNAM.AI, Hack Core PS-07).

CORE OPERATING DIRECTIVES:
1. SCIENTIFIC & ADVISORY INTEGRITY:
   • Never make claims of 'guaranteed profit', 'ensure 100% yield', or 'will definitely increase yield'.
   • Always use probabilistic, evidence-based advisory language (e.g., 'calibrated models project an estimated response of...', 'recommended best practice indicates...', 'subject to weather and field conditions').
   • Clearly distinguish measured field telemetry from modeled estimates or demonstration data.
2. SYNCHRONIZED FARM CONTEXT: Reference the contextual numbers provided in the [SYNCHRONIZED FARM TELEMETRY] block (temperature, soil parameters, Agmarknet mandi benchmarks).
3. ONLY if an audio clip is actually attached, transcribe their exact spoken query first under: "**🗣️ Transcribed Voice Query:** <query>". If no audio is attached, never mention transcription or voice queries.
4. If the user provided an IMAGE (leaf/crop/pest), evaluate visual symptoms and remind the user that AI visual screening is preliminary and should be verified with an agronomist or local KVK expert.
5. Prescriptions must be balanced: specify crop, dosage unit (g/L or ml/acre), application timing, safety pre-harvest interval (PHI), and non-chemical/regenerative biocontrol alternatives (*Trichoderma*, *Pseudomonas*, neem oil).
6. Deliver a clear CACP/Agmarknet economic perspective, noting market assumptions transparently.
7. Respond fluently and respectfully in the farmer's requested language.
"""

def build_context_block(ctx: dict) -> str:
    """Builds a rich structured farm context string from the full context dict."""
    if not ctx:
        return ""
    lines = ["\n[SYNCHRONIZED FARM TELEMETRY — Live Platform Telemetry]"]

    # Location & Crop
    if ctx.get("region"):      lines.append(f"• Farm Location  : {ctx['region']}")
    if ctx.get("lat") and ctx.get("lon"):
        lines.append(f"• GPS Coordinates: {ctx['lat']:.4f}°N, {ctx['lon']:.4f}°E")
    if ctx.get("crop"):        lines.append(f"• Target Crop    : {ctx['crop']}")
    if ctx.get("product"):     lines.append(f"• Biological Input: {ctx['product']} @ {ctx.get('dosage', 'recommended')} L/acre")

    # Live Weather & Stress
    if ctx.get("temp_max"):    lines.append(f"• Current Temp   : {ctx['temp_max']:.1f}°C (Max) / {ctx.get('temp_min', 0):.1f}°C (Min)")
    if ctx.get("humidity"):    lines.append(f"• Air Humidity   : {ctx['humidity']:.0f}% RH")
    if ctx.get("wind_speed"):  lines.append(f"• Wind Speed     : {ctx['wind_speed']} km/h")
    if ctx.get("rainfall"):    lines.append(f"• Season Rainfall: {ctx['rainfall']:.0f} mm")
    if ctx.get("heat_stress"): lines.append(f"• Heat Stress Days: {ctx['heat_stress']} days (>35°C thermal threshold)")

    # DAC&FW National Soil Health Card Benchmarks
    if ctx.get("nitrogen"):
        n_val = ctx['nitrogen']
        n_st = "DEFICIENT ⚠️ (<280 kg/ha)" if n_val < 280 else ("OPTIMAL ✅ (280-560)" if n_val <= 560 else "HIGH")
        lines.append(f"• Soil Nitrogen (N)  : {n_val:.0f} kg/ha [{n_st}]")
    if ctx.get("phosphorus"):
        p_val = ctx['phosphorus']
        p_st = "DEFICIENT ⚠️ (<23 kg/ha)" if p_val < 23 else ("OPTIMAL ✅ (23-56)" if p_val <= 56 else "HIGH")
        lines.append(f"• Soil Phosphorus (P): {p_val:.0f} kg/ha [{p_st}]")
    if ctx.get("potassium"):
        k_val = ctx['potassium']
        k_st = "DEFICIENT ⚠️ (<145 kg/ha)" if k_val < 145 else ("OPTIMAL ✅ (145-336)" if k_val <= 336 else "HIGH")
        lines.append(f"• Soil Potassium (K) : {k_val:.0f} kg/ha [{k_st}]")
    if ctx.get("ph"):          lines.append(f"• Soil Reaction (pH) : {ctx['ph']:.1f}")
    if ctx.get("soc"):         lines.append(f"• Organic Carbon (SOC): {ctx['soc']:.2f}% ({'Low <0.5%' if ctx['soc'] < 0.5 else 'Adequate'})")

    # Agmarknet 2.0 Live Mandi Pulse
    if ctx.get("mandi_spot"):
        lines.append(f"• Mandi Modal Spot Rate: Rs {ctx['mandi_spot']:,.0f} / quintal")
    if ctx.get("mandi_msp"):
        lines.append(f"• Govt MSP Floor Price : Rs {ctx['mandi_msp']:,.0f} / quintal")
    if ctx.get("mandi_verdict"):
        lines.append(f"• Mandi Market Verdict : {ctx['mandi_verdict']}")
    if ctx.get("mandi_trend"):
        lines.append(f"• 72h Price Momentum   : {ctx['mandi_trend']}")
    if ctx.get("quality_premium"):
        lines.append(f"• Grade-A Quality Bonus: +Rs {ctx['quality_premium']:,.0f}/quintal")

    # Outcome & Attribution
    if ctx.get("predicted_yield"):
        lines.append(f"• Total Yield Predicted : {ctx['predicted_yield']:.2f} q/acre")
    if ctx.get("yield_delta"):
        lines.append(f"• Biological Yield Boost: +{ctx['yield_delta']:.2f} q/acre")
    if ctx.get("net_profit"):
        lines.append(f"• Net Farm Profit Lift  : Rs {ctx['net_profit']:,.0f} / acre")
    if ctx.get("roi_pct"):
        lines.append(f"• Return on Investment  : {ctx['roi_pct']:.1f}%")

    lines.append("[END SYNCHRONIZED TELEMETRY]\n")
    return "\n".join(lines)


def generate_domain_expert_fallback(user_query: str, language: str, context_info: dict = None) -> str:
    """Robust offline agronomic response in the selected language."""
    ctx = context_info or {}
    crop = ctx.get("crop", "Crop")
    product = ctx.get("product", "Syngenta Quantis")
    heat_stress = ctx.get("heat_stress", 5)
    n_val = ctx.get("nitrogen", 210)
    mandi = ctx.get("mandi_spot", 5869)
    profit = ctx.get("net_profit", 14573)

    lang_lower = str(language).lower()
    if "marathi" in lang_lower or "मराठी" in lang_lower:
        return f"""
🌾 **कृषी-सल्लागार प्रत्यक्ष मार्गदर्शन ({crop}):**

1. **जैविक फवारणी वेळ:** {product} ची फवारणी सकाळी ८ ते १०:३० किंवा संध्याकाळी ४:३० नंतर करावी (दुपारचे ३२°C पेक्षा जास्त तापमान टाळा).
2. **उष्णता तणाव संरक्षण:** शेतात {heat_stress} दिवसांचा उष्णता ताण असल्याने फुलगळ रोखण्यासाठी २ मिली प्रति लिटर पाण्यात मिसळून फवारणी करा.
3. **मातीतील नत्र (N):** मातीतील नत्र {n_val:.0f} kg/ha आहे (मानक २८० kg/ha पेक्षा कमी). २५ kg/ha युरियासोबत बायो-स्टिम्युलेटर वापरल्यास अन्नद्रव्य शोषण क्षमता वाढेल.
4. **अगमार्कनेट २.० बाजारभाव:** आजचा लाइव्ह मंडी दर ₹{mandi:,.0f}/क्विंटल आहे. सिंजेंटा ग्रेड-A गुणवत्तेमुळे जास्तीचा प्रीमियम मिळेल.
5. **अपेक्षित नफा:** एकरी अंदाजे ₹{profit:,.0f} चा निव्वळ नफा शक्य आहे!
"""
    elif "hindi" in lang_lower or "हिंदी" in lang_lower:
        return f"""
🌾 **कृषि-सलाहकार वास्तविक मार्गदर्शन ({crop}):**

1. **जैविक छिड़काव का समय:** {product} का छिड़काव सुबह 8 से 10:30 बजे या शाम 4:30 बजे के बाद करें। दोपहर की 32°C से अधिक गर्मी से बचें।
2. **ताप-तनाव सुरक्षा:** खेत में {heat_stress} दिनों के अत्यधिक तापमान के कारण फूल झड़ने से रोकने हेतु 2 मिली प्रति लीटर पानी में मिलाकर छिड़कें।
3. **मिट्टी में नाइट्रोजन (N):** आपकी मिट्टी में N = {n_val:.0f} kg/ha है (सरकारी मानक 280 kg/ha से कम)। जैव-उत्तेजक जड़ों की अवशोषण क्षमता 30% तक बढ़ाते हैं।
4. **एगमार्कनेट 2.0 मंडी भाव:** आज का मंडी भाव ₹{mandi:,.0f}/क्विंटल है। ग्रेड-A गुणवत्ता से अतिरिक्त प्रीमियम मिलेगा।
5. **आर्थिक लाभ:** प्रति एकड़ लगभग ₹{profit:,.0f} का अतिरिक्त शुद्ध मुनाफा सुनिश्चित किया जा सकता है!
"""
    elif "punjabi" in lang_lower or "ਪੰਜਾਬੀ" in lang_lower or "pa" in lang_lower:
        return f"""
🌾 **ਖੇਤੀਬਾੜੀ ਸਲਾਹਕਾਰ ਲਾਈਵ ਮਾਰਗਦਰਸ਼ਨ ({crop}):**

1. **ਜੈਵਿਕ ਸਪਰੇਅ ਦਾ ਸਮਾਂ:** {product} ਦਾ ਛਿੜਕਾਅ ਸਵੇਰੇ 8 ਤੋਂ 10:30 ਵਜੇ ਜਾਂ ਸ਼ਾਮ 4:30 ਵਜੇ ਤੋਂ ਬਾਅਦ ਕਰੋ (ਦੁਪਹਿਰ ਦੀ 32°C ਤੋਂ ਵੱਧ ਗਰਮੀ ਤੋਂ ਬਚੋ)।
2. **ਗਰਮੀ ਦੇ ਤਣਾਅ ਤੋਂ ਸੁਰੱਖਿਆ:** ਖੇਤ ਵਿੱਚ {heat_stress} ਦਿਨਾਂ ਦੇ ਤੇਜ਼ ਤਾਪਮਾਨ ਕਾਰਨ ਫੁੱਲ ਡਿੱਗਣ ਤੋਂ ਰੋਕਣ ਲਈ 2 ਮਿਲੀਲੀਟਰ ਪ੍ਰਤੀ ਲੀਟਰ ਪਾਣੀ ਵਿੱਚ ਮਿਲਾ ਕੇ ਛਿੜਕੋ।
3. **ਮਿੱਟੀ ਵਿੱਚ ਨਾਈਟ੍ਰੋਜਨ (N):** ਤੁਹਾਡੀ ਮਿੱਟੀ ਵਿੱਚ N = {n_val:.0f} kg/ha ਹੈ (ਸਰਕਾਰੀ ਮਾਪਦੰਡ 280 kg/ha ਤੋਂ ਘੱਟ)। ਜੈਵਿਕ ਉਤੇਜਕ ਜੜ੍ਹਾਂ ਦੀ ਖੁਰਾਕ ਲੈਣ ਦੀ ਸਮਰੱਥਾ 30% ਤੱਕ ਵਧਾਉਂਦੇ ਹਨ।
4. **ਐਗਮਾਰਕਨੈੱਟ 2.0 ਮੰਡੀ ਭਾਅ:** ਅੱਜ ਦਾ ਲਾਈਵ ਮੰਡੀ ਭਾਅ ₹{mandi:,.0f}/ਕੁਇੰਟਲ ਹੈ। ਸਿੰਜੈਂਟਾ ਗ੍ਰੇਡ-A ਕੁਆਲਿਟੀ ਨਾਲ ਵਾਧੂ ਪ੍ਰੀਮੀਅਮ ਮਿਲੇਗਾ।
5. **ਅਨੁਮਾਨਿਤ ਮੁਨਾਫਾ:** ਪ੍ਰਤੀ ਏਕੜ ਲਗਭਗ ₹{profit:,.0f} ਦਾ ਵਾਧੂ ਸ਼ੁੱਧ ਮੁਨਾਫਾ ਸੰਭਵ ਹੈ!
"""
    elif "telugu" in lang_lower or "తెలుగు" in lang_lower:
        return f"""
🌾 **వ్యవసాయ నిపుణుల సలహా ({crop}):**

1. **పిచికారీ సమయం:** {product} ను ఉదయం 8 నుండి 10:30 గంటల మధ్య లేదా సాయంత్రం 4:30 తర్వాత పిచికారీ చేయండి (మధ్యాహ్నం 32°C ఎండను నివారించండి).
2. **ఎండ వేడిమి రక్షణ:** పొలంలో {heat_stress} రోజుల వేడి ప్రభావం వల్ల పూత రాలకుండా నివారించడానికి లీటరు నీటికి 2 మి.లీ కలిపి వాడండి.
3. **భూమిలో నత్రజని (N):** నత్రజని {n_val:.0f} kg/ha ఉంది (DAC&FW ప్రామాణికం 280 kg/ha కంటే తక్కువ).
4. **అగ్‌మార్క్‌నెట్ 2.0 మండి ధర:** ఈరోజు స్పాట్ ధర ₹{mandi:,.0f}/క్వింటాల్. గ్రేడ్-A నాణ్యతతో అదనపు ప్రీమియం పొందవచ్చు.
5. **ఆశించిన లాభం:** ఎకరానికి ₹{profit:,.0f} నికర లాభం సాధ్యమవుతుంది!
"""
    else:
        english_briefing = f"""
**AgriAttribute Field Intelligence Briefing ({crop}):**

**Core Verdict:** Your live farm telemetry indicates {f'soil nitrogen deficiency ({n_val:.0f} kg/ha vs 280 kg/ha DAC&FW benchmark)' if n_val < 280 else 'stable soil nutrients'} and {heat_stress} days of heat stress.

1. **Application Protocol:** Spray {product} at 2.0 L/acre (or 2 mL/L water) strictly between 8:00 AM – 10:30 AM or after 4:30 PM. Use 400-500 L/ha water with hollow-cone nozzles.
2. **Heat Stress Defense:** Thermal stress (>35°C) triggers ethylene release causing flower/boll abortion. Biostimulants maintain cell turgor and restore stomatal conductance.
3. **Soil Nutrient Synergy:** With soil N at {n_val:.0f} kg/ha, biostimulants improve root nutrient scavenging by up to 30%, enabling a 15% reduction in synthetic urea.
4. **Agmarknet 2.0 Market Opportunity:** Today's APMC modal spot rate is Rs {mandi:,.0f}/q. Grade-A bolder grain quality fetches an additional quality auction premium.

**Economic Bottom Line:** Total estimated net profit lift is Rs {profit:,.0f}/acre.
"""
        # If farmer selected an Indic language (Gujarati, Tamil, Kannada, Bengali, etc.), translate dynamically via IndicTrans2
        if lang_lower and lang_lower not in ["english", "en"]:
            try:
                from services import indictrans_service
                return indictrans_service.translate_en_to_indic(english_briefing, language)
            except Exception:
                pass
        return english_briefing


def ask_gemini_multimodal(
    query_text: str = None,
    audio_bytes: bytes = None,
    audio_mime: str = "audio/wav",
    image_bytes: bytes = None,
    image_mime: str = "image/jpeg",
    language: str = "English",
    context_info: dict = None
) -> dict:
    """
    Multimodal Gemini 2.5 Flash query handler:
    Accepts direct Audio Voice Notes (raw bytes from microphone), Field Photos, and Text Queries,
    fused with the synchronized live farm telemetry.
    """
    context_block = build_context_block(context_info)
    
    parts = []

    # 1. Attach Audio Voice Note if provided
    has_audio = False
    if audio_bytes and len(audio_bytes) > 100:
        has_audio = True
        try:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": audio_mime,
                    "data": b64_audio
                }
            })
        except Exception:
            has_audio = False

    # 2. Attach Image if provided
    has_image = False
    if image_bytes and len(image_bytes) > 100:
        has_image = True
        try:
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": image_mime,
                    "data": b64_img
                }
            })
        except Exception:
            has_image = False

    # 3. Construct the comprehensive instruction prompt
    instructions = [AGRI_SYSTEM_PROMPT, context_block, f"[Target Language: {language}]"]

    if has_audio:
        instructions.append(
            "IMPORTANT: An audio voice note is attached. First, transcribe the farmer's spoken query verbatim in its original language, label it '**🗣️ Spoken Question:** <text>'. Then, formulate a direct, actionable answer in the target language referencing the synchronized telemetry."
        )
    if has_image:
        instructions.append(
            "IMPORTANT: A field photograph is attached. Diagnose any visual symptoms (chlorosis, spots, lesions, deficiency, pest infestation), correlate with the farm soil & weather, and provide treatment recommendations."
        )

    canonical_query = query_text
    is_indic = language and str(language).lower() not in ["english", "en"]
    if is_indic and query_text and query_text.strip():
        try:
            from services import indictrans_service
            translated_q = indictrans_service.translate_indic_to_en(query_text.strip(), language)
            if translated_q and translated_q != query_text.strip():
                canonical_query = translated_q
        except Exception:
            pass

    if query_text and query_text.strip():
        if canonical_query and canonical_query != query_text.strip():
            instructions.append(f"Farmer's Original Query ({language}): {query_text.strip()}")
            instructions.append(f"Canonical English Query (translated): {canonical_query.strip()}")
        else:
            instructions.append(f"Farmer's Written Query: {query_text.strip()}")
    elif not has_audio and not has_image:
        instructions.append("Farmer requested an overall executive field advisory based on today's farm telemetry.")

    instructions.append("\nAgriAttribute AI Field Co-Pilot Response:")
    full_prompt_text = "\n".join(instructions)

    parts.append({"text": full_prompt_text})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 950,
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }

    api_key = _get_gemini_key()
    if api_key:
        try:
            # Key goes in a header, not the URL, so it never lands in logs or tracebacks (see generate_content).
            data, used_model = generate_content(payload, timeout=30)
            if data:
                reply = response_text(data)
                if reply and len(reply.strip()) > 10:
                    final_reply = reply.strip()
                    # If target is Indic language but model responded in English, translate via IndicTrans2
                    if is_indic:
                        try:
                            from services import indictrans_service
                            ascii_chars = sum(1 for c in final_reply if ord(c) < 128)
                            if len(final_reply) > 0 and (ascii_chars / len(final_reply)) > 0.85:
                                translated_reply = indictrans_service.translate_en_to_indic(final_reply, language)
                                if translated_reply:
                                    final_reply = translated_reply
                        except Exception:
                            pass
                    return {
                        "status": "LIVE",
                        "source": model_label(used_model),
                        "translation_engine": _translation_engine_label(),
                        "response": final_reply,
                        "language": language,
                        "canonical_query": canonical_query,
                        "has_audio": has_audio,
                        "has_image": has_image
                    }
        except Exception:
            pass

    # Graceful fallback to verified agronomic rule-based expert engine + IndicTrans2
    fallback_text = generate_domain_expert_fallback(query_text or "General field advice", language, context_info)
    return {
        "status": "DEMO / SYNTHETIC",
        "source": "Offline Agronomic Expert Engine",
        "translation_engine": _translation_engine_label(),
        "response": fallback_text.strip(),
        "language": language,
        "canonical_query": canonical_query,
        "has_audio": has_audio,
        "has_image": has_image
    }


def ask_gemini_agri_assistant(user_query: str, language: str = "English", context_info: dict = None) -> dict:
    """Backwards-compatible wrapper calling the multimodal engine."""
    return ask_gemini_multimodal(
        query_text=user_query,
        language=language,
        context_info=context_info
    )


def generate_voice_speech_html(text_to_speak: str, lang_code: str = "en-IN") -> str:
    """
    Browser Web Speech Synthesis widget — plays Gemini's advice aloud in native dialect.
    """
    clean_text = text_to_speak.replace('"', '\\"').replace('\n', ' ')
    clean_text = html_mod.escape(clean_text)

    lang_tag = "en-IN"
    btn_label = "🔊 Listen to Advice"
    l_low = lang_code.lower()
    if "hi" in l_low or "hindi" in l_low:
        lang_tag = "hi-IN"
        btn_label = "🔊 सलाह सुनें"
    elif "mr" in l_low or "marathi" in l_low:
        lang_tag = "mr-IN"
        btn_label = "🔊 सल्ला ऐका"
    elif "pa" in l_low or "punjabi" in l_low or "ਪੰਜਾਬੀ" in l_low:
        lang_tag = "pa-IN"
        btn_label = "🔊 ਸਲਾਹ ਸੁਣੋ"
    elif "te" in l_low or "telugu" in l_low:
        lang_tag = "te-IN"
        btn_label = "🔊 సలహా వినండి"
    elif "gu" in l_low or "gujarati" in l_low:
        lang_tag = "gu-IN"
        btn_label = "🔊 સલાહ સાંભળો"
    elif "kn" in l_low or "kannada" in l_low:
        lang_tag = "kn-IN"
        btn_label = "🔊 ಸಲಹೆ ಕೇಳಿ"
    elif "ta" in l_low or "tamil" in l_low:
        lang_tag = "ta-IN"
        btn_label = "🔊 ஆலோசனையைக் கேளுங்கள்"
    elif "bn" in l_low or "bengali" in l_low:
        lang_tag = "bn-IN"
        btn_label = "🔊 পরামর্শ শুনুন"

    return f"""
<div style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">
    <button onclick="speakAgriText()" style="background:#059669; color:white; border:none;
        padding:8px 16px; border-radius:20px; cursor:pointer; font-weight:700;
        font-size:0.85rem; display:inline-flex; align-items:center; gap:6px;
        box-shadow:0 2px 8px rgba(5,150,105,0.3);">
        {btn_label}
    </button>
    <button onclick="window.speechSynthesis.cancel()" style="background:#f1f5f9;
        color:#475569; border:1px solid #cbd5e1; padding:8px 12px;
        border-radius:20px; cursor:pointer; font-weight:600; font-size:0.85rem;">
        ⏹️ Stop
    </button>
    <script>
        function speakAgriText() {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                var msg = new SpeechSynthesisUtterance("{clean_text}");
                msg.lang = "{lang_tag}";
                msg.rate = 0.92;
                window.speechSynthesis.speak(msg);
            }} else {{
                alert('Speech synthesis not supported on this browser.');
            }}
        }}
    </script>
</div>
"""

def get_engine_status() -> dict:
    """Returns the operational status of the Gemini conversational service and IndicTrans2 translation bridge."""
    key = _get_gemini_key()
    indic_status = {}
    try:
        from services import indictrans_service
        indic_status = indictrans_service.get_translation_status()
    except Exception:
        pass

    if key:
        return {
            "status": "LIVE",
            "model": "Gemini 2.5 Flash",
            "translation_engine": _translation_engine_label(),
            "api_configured": True,
            "indictrans_details": indic_status
        }
    return {
        "status": "DEMO / SYNTHETIC",
        "model": "Offline Agronomic Expert Engine",
        "translation_engine": _translation_engine_label(),
        "api_configured": False,
        "indictrans_details": indic_status
    }

def get_offline_expert_response(query: str, language: str = "English", context_info: dict = None) -> str:
    """Direct wrapper for offline expert knowledge fallback."""
    return generate_domain_expert_fallback(query, language, context_info)


def render_gemini_chat_interface(
    lang: str = "English",
    crop: str = "Soybean",
    region: str = "Maharashtra & Vidarbha (Deccan)",
    ow_live: dict = None,
    mandi_info: dict = None,
    pred_actual: float = 24.0,
    yield_delta: float = 3.5,
    net_profit: float = 12500.0,
    roi_pct: float = 180.0,
    bio_product: str = "Syngenta Quantis",
    heat_stress: int = 2,
    rainfall: float = 450.0,
    n_val: float = 240.0,
    p_val: float = 22.0,
    k_val: float = 185.0,
    ph: float = 7.6,
    soc: float = 4.8,
    t = None,
    t_crop = None
):
    """
    Renders the complete Multilingual Gemini 2.5 Flash Field Agronomist interface for tab_ai.
    Integrates Text, Audio Voice Notes, Leaf/Crop Photos, and Browser Web Speech Synthesis.
    """
    import streamlit as st
    ow = ow_live or {}
    mandi = mandi_info or {}
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%); border: 1.5px solid #a7f3d0; border-radius: 16px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 4px 16px rgba(16,185,129,0.08);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: #ecfdf5; border: 1.5px solid #86efac; width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.6rem;">
                    🤖
                </div>
                <div>
                    <div style="font-size: 1.25rem; font-weight: 900; color: #064e3b;">
                        Gemini 2.5 Flash Multilingual Field Agronomist & Voice Co-Pilot
                    </div>
                    <div style="font-size: 0.82rem; color: #166534; font-weight: 600;">
                        Multilingual (English, Hindi, Marathi, Telugu) • Multimodal Image &amp; Voice Reasoning
                    </div>
                </div>
            </div>
            <span style="background: #ecfdf5; border: 1.5px solid #86efac; color: #047857; font-size: 0.78rem; font-weight: 800; padding: 4px 14px; border-radius: 20px;">
                ⚡ Synchronized Live Farm Telemetry
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Telemetry Context Dictionary
    context_pkg = {
        "region": region,
        "crop": crop,
        "product": bio_product,
        "temp_max": safe_float(ow.get("temp_c", 28.5), 28.5),
        "temp_min": safe_float(ow.get("feels_like_c", 25.0), 25.0),
        "humidity": safe_float(ow.get("humidity_pct", 65), 65.0),
        "wind_speed": safe_float(ow.get("wind_speed_kmh", 10.0), 10.0),
        "rainfall": safe_float(rainfall, 0.0),
        "heat_stress": safe_int(heat_stress, 0),
        "nitrogen": safe_float(n_val, 120.0),
        "phosphorus": safe_float(p_val, 60.0),
        "potassium": safe_float(k_val, 40.0),
        "ph": safe_float(ph, 6.8),
        "soc": safe_float(soc, 0.65),
        "mandi_spot": safe_float(mandi.get("realizable_price", 5200.0), 5200.0),
        "mandi_msp": safe_float(mandi.get("msp", 4892.0), 4892.0),
        "predicted_yield": safe_float(pred_actual, 24.0),
        "yield_delta": safe_float(yield_delta, 0.0),
        "net_profit": safe_float(net_profit, 0.0),
        "roi_pct": safe_float(roi_pct, 0.0)
    }

    # Preset Quick Prompts
    st.markdown("##### 💡 Quick Farmer Questions")
    q_cols = st.columns(3)
    p1 = f"What is the best spray time for {crop} under current weather?"
    p2 = f"How does {bio_product} buffer my field against {heat_stress} heat stress days?"
    p3 = f"Explain my net profit lift of ₹{net_profit:,.0f}/acre and ROI calculation."

    if "gemini_user_query" not in st.session_state:
        st.session_state.gemini_user_query = ""

    with q_cols[0]:
        if st.button("🌡️ Spray Timing & Safety Window", width="stretch", key="qp1"):
            st.session_state.gemini_user_query = p1
    with q_cols[1]:
        if st.button("🧬 Biostimulant Stress Priming", width="stretch", key="qp2"):
            st.session_state.gemini_user_query = p2
    with q_cols[2]:
        if st.button("💰 Net Profit & ROI Breakdown", width="stretch", key="qp3"):
            st.session_state.gemini_user_query = p3

    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        user_text = st.text_input(
            "Ask your Agronomist Question (Supports English, Hindi, Marathi, Punjabi, Telugu, etc.):",
            value=st.session_state.gemini_user_query,
            key="ai_chat_text_input",
            placeholder="e.g. My leaves have yellow spots. When should I apply biostimulant?"
        )
    with col_in2:
        image_file = st.file_uploader(
            "📷 Upload Leaf / Crop Photo (Optional):",
            type=["jpg", "jpeg", "png", "webp"],
            key="ai_chat_img_uploader"
        )

    img_bytes = None
    if image_file is not None:
        try:
            img_bytes = image_file.read()
            st.image(image_file, caption="Uploaded Specimen", width=200)
        except Exception:
            img_bytes = None

    if st.button("🚀 Ask Gemini Agronomist", type="primary", width="stretch", key="btn_ask_gemini"):
        query = user_text.strip() if user_text else "Provide an executive agronomy advisory for my field."
        with st.spinner("Gemini 2.5 Flash analyzing farm telemetry and formulating response..."):
            res = ask_gemini_multimodal(
                query_text=query,
                image_bytes=img_bytes,
                language=lang,
                context_info=context_pkg
            )

        resp_text = res.get("response", "")
        status_src = res.get("source", "Google Gemini 2.5 Flash")

        st.markdown(f"""
        <div style="background: #ffffff; border: 2px solid #10b981; border-radius: 14px; padding: 18px 22px; margin-top: 16px; box-shadow: 0 4px 16px rgba(16,185,129,0.08);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                <span style="font-size: 1.05rem; font-weight: 800; color: #065f46;">🌱 Field Agronomist Advisory Response</span>
                <span style="background: #ecfdf5; border: 1px solid #86efac; color: #047857; font-size: 0.72rem; font-weight: 800; padding: 3px 10px; border-radius: 12px;">
                    {status_src}
                </span>
            </div>
            <div style="font-size: 0.95rem; color: #0f172a; line-height: 1.6; white-space: pre-wrap;">
{resp_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Render Web Speech Audio Button
        st.markdown(generate_voice_speech_html(resp_text, lang_code=lang), unsafe_allow_html=True)


