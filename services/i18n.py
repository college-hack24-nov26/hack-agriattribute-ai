"""
i18n.py - one translation layer under the whole app.

Why: only part of the app used the translation table; many labels, buttons, headings and HTML cards were plain
English. Instead of translating screen by screen, this module wraps the Streamlit calls that show text
(markdown, captions, buttons, tab and widget labels, tables, charts ...) and translates what they show.

How it works
  * Text is split into a template: numbers become placeholders (so "Wind is 8 km/h" and "Wind is 12 km/h" share one
    translation) and, for HTML, only the visible text between tags is translated, never tags, styles or attributes.
  * Translations live in data/i18n/<code>.json, so a language is translated once and then loads instantly and offline.
  * Text with no cached translation is shown in English, queued, translated in one batch with Gemini, saved, and the
    page re-runs once. Marathi and Hindi are pre-translated from the app's real text.
  * Widget values are never changed, only what the user reads (selectbox options use format_func).

The translator keeps product names, units and numbers, and uses short farmer-friendly words.
"""

import functools
import html as html_mod
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Optional, Set

import streamlit as st

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DIR = os.path.join(_ROOT, "data", "i18n")
LANGS = {"mr": "Marathi", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "kn": "Kannada", "gu": "Gujarati", "bn": "Bengali", "pa": "Punjabi"}
_PREFIX = {"hindi": "hi", "marathi": "mr", "telugu": "te", "tamil": "ta", "kannada": "kn", "gujarati": "gu", "bengali": "bn", "punjabi": "pa"}

_LOCK = threading.Lock()
_CACHE: Dict[str, Dict[str, str]] = {}
_PENDING: Dict[str, Set[str]] = {}
_ATTEMPTED: Dict[str, Set[str]] = {}
_MEMO: Dict[Any, str] = {}
SEEN: Set[str] = set()          # recorder: every template the app tried to show (used to pre-translate)
RECORD = False
_INSTALLED = False

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_PH = re.compile(r"⟦\s*(\d+)\s*⟧")
_LATIN = re.compile(r"[A-Za-z]{2,}")
_INDIC = re.compile(r"[ऀ-෿਀-੿]")      # already in an Indian script (or a native language name): leave alone
_URLISH = re.compile(r"(https?://|www\.|\.(png|jpg|jpeg|svg|gif|css|js|pdf|csv|xlsx|json)\b|^[#./\\])", re.I)

# Unicode block of each language's script. Small models sometimes answer in Hindi when asked for Telugu, so a
# translation is kept only if every Indian-script letter in it belongs to the target script.
_SCRIPT = {"hi": (0x0900, 0x097F), "mr": (0x0900, 0x097F), "bn": (0x0980, 0x09FF), "pa": (0x0A00, 0x0A7F),
           "gu": (0x0A80, 0x0AFF), "ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF)}


def right_script(text: str, code: str) -> bool:
    lo, hi = _SCRIPT.get(code, (0, 0x10FFFF))
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x0DFF and not (lo <= o <= hi or o in (0x0964, 0x0965)):   # danda is shared
            return False
    return True


def purge_wrong_script(code: str) -> int:
    """Removes cached translations written in the wrong script; returns how many were dropped."""
    cache = _load(code)
    bad = [k for k, v in cache.items() if not right_script(v, code)]
    for k in bad:
        cache.pop(k, None)
    if bad:
        _save(code)
        _MEMO.clear()
    return len(bad)

GLOSSARY = ("mandi = मंडी style local word kept as the commonly used term; quintal (q) = the local unit क्विंटल; "
            "biological / biostimulant = the commonly used local term; ROI = keep 'ROI'; yield = crop production per acre; "
            "keep product names (Quantis, Megafol, Isabion, Vixeran ...), company and API names, units (kg, q, mm, km/h, °C, %), "
            "currency symbols and emoji exactly.")


# ---------------------------------------------------------------------------
# language + files
# ---------------------------------------------------------------------------
def code_for(lang: Optional[str]) -> Optional[str]:
    """'Marathi (मराठी)' -> 'mr'; English or unknown -> None (no translation)."""
    l = (lang or "English").strip().lower()
    for prefix, code in _PREFIX.items():
        if l.startswith(prefix):
            return code
    return None


def _path(code: str) -> str:
    return os.path.join(_DIR, f"{code}.json")


def _load(code: str) -> Dict[str, str]:
    with _LOCK:
        if code not in _CACHE:
            try:
                with open(_path(code), "r", encoding="utf-8") as f:
                    _CACHE[code] = json.load(f)
            except (OSError, ValueError):
                _CACHE[code] = {}
        return _CACHE[code]


def _save(code: str) -> None:
    os.makedirs(_DIR, exist_ok=True)
    tmp = _path(code) + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_CACHE.get(code, {}), f, ensure_ascii=False, indent=0, sort_keys=True)
        os.replace(tmp, _path(code))


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------
def _templatize(text: str):
    vals: List[str] = []

    def sub(m):
        vals.append(m.group(0))
        return f"⟦{len(vals) - 1}⟧"

    return _NUM.sub(sub, text), vals


def _restore(tpl: str, vals: List[str]) -> str:
    return _PH.sub(lambda m: vals[int(m.group(1))] if int(m.group(1)) < len(vals) else m.group(0), tpl)


def _worth(text: str) -> bool:
    t = text.strip()
    if len(t) < 2 or not _LATIN.search(t) or _INDIC.search(t) or _URLISH.search(t) or t.startswith("```"):
        return False
    return True


# Markdown that starts a line (heading, bullet, numbered item, quote) is kept as is; only the words after it
# are translated. Without this a heading such as "#### Your offers" looked like a URL anchor and was skipped.
_MD_PREFIX = re.compile(r"^(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s*)+")


def _translate_piece(piece: str, code: str) -> str:
    """One visible text run (no HTML tags). Returns it translated when cached, else queues it."""
    lead = piece[: len(piece) - len(piece.lstrip())]
    trail = piece[len(piece.rstrip()):]
    core = piece.strip()
    if "\n" in core:
        # a cached translation of the whole block wins; otherwise translate line by line (headings and lists
        # keep their markdown, and lines are reused across screens)
        tpl, vals = _templatize(core)
        hit = _load(code).get(tpl)
        if hit:
            return lead + _restore(hit, vals) + trail
        return lead + "\n".join(_translate_piece(line, code) for line in core.split("\n")) + trail
    m = _MD_PREFIX.match(core)
    if m:
        return lead + m.group(0) + _translate_piece(core[m.end():], code) + trail
    if not _worth(core):
        return piece
    tpl, vals = _templatize(core)
    if RECORD:
        SEEN.add(tpl)
    hit = _load(code).get(tpl)
    if hit:
        return lead + _restore(hit, vals) + trail
    if tpl not in _ATTEMPTED.setdefault(code, set()):
        _PENDING.setdefault(code, set()).add(tpl)
    return piece


_TAG = re.compile(r"(<[^>]+>)")


def _translate_html(s: str, code: str) -> str:
    out: List[str] = []
    skip = False
    for part in _TAG.split(s):
        if _TAG.fullmatch(part or ""):
            low = part.lower()
            if low.startswith("<style") or low.startswith("<script"):
                skip = True
            elif low.startswith("</style") or low.startswith("</script"):
                skip = False
            out.append(part)
        elif skip or not part.strip():
            out.append(part)
        else:
            raw = html_mod.unescape(part)
            new = _translate_piece(raw, code)
            out.append(part if new == raw else html_mod.escape(new, quote=False))
    return "".join(out)


def tr(s: Any, code: Optional[str]) -> Any:
    """Translate a string (plain, markdown or HTML) for language code; anything else is returned untouched."""
    if not isinstance(s, str) or not s:
        return s
    if RECORD and not code:
        _translate_html(s, "__rec__") if ("<" in s and ">" in s) else _translate_piece(s, "__rec__")
        return s
    if not code:
        return s
    key = (s, code)
    if key in _MEMO:
        return _MEMO[key]
    before = len(_PENDING.get(code, ()))
    out = _translate_html(s, code) if ("<" in s and ">" in s) else _translate_piece(s, code)
    if len(_PENDING.get(code, ())) == before:     # fully resolved: safe to remember
        if len(_MEMO) > 20000:
            _MEMO.clear()
        _MEMO[key] = out
    return out


def _any(x: Any, code: Optional[str]) -> Any:
    if isinstance(x, str):
        return tr(x, code)
    if isinstance(x, (list, tuple)):
        return type(x)(tr(i, code) if isinstance(i, str) else i for i in x)
    return x


# ---------------------------------------------------------------------------
# batch translation (Gemini)
# ---------------------------------------------------------------------------
def _gemini_key() -> str:
    try:
        from services import gemini_service
        return gemini_service._get_gemini_key()
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


QUOTA_WAIT_S = 0.0      # in the app never wait for a rate limit; the offline seeder sets this higher


def _gemini_batch(strings: List[str], language: str) -> Optional[List[str]]:
    key = _gemini_key()
    if not key or not strings:
        return None
    prompt = (f"Translate these short UI strings of a farming app from English to {language}. Use simple words a farmer in India "
              f"understands. Keep every placeholder like ⟦0⟧ exactly as written, keep markdown (**bold**, `code`) and any "
              f"HTML entities. {GLOSSARY} Return ONLY a JSON array of {len(strings)} strings, in the same order.\n"
              + json.dumps(strings, ensure_ascii=False))
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json", "maxOutputTokens": 16000,
                                 "thinkingConfig": {"thinkingBudget": 0}}}
    from services import gemini_service            # model fallback + quota cool-down live there
    try:
        resp, _model = gemini_service.generate_content(body, timeout=90, wait_s=QUOTA_WAIT_S)
        if not resp:
            raise _Unavailable()
        data = json.loads(gemini_service.response_text(resp))
    except _Unavailable:
        raise
    except Exception:
        return None
    if isinstance(data, list) and len(data) == len(strings) and all(isinstance(x, str) for x in data):
        return data
    return None


class _Unavailable(Exception):
    """No Gemini model answered (quota, network or key): stop instead of retrying chunk by chunk."""


def _translate_strings(strings: List[str], code: str) -> Dict[str, str]:
    """Translates templates in chunks (parallel). A chunk that comes back malformed is split and retried."""
    language = LANGS.get(code, code)
    result: Dict[str, str] = {}

    def work(chunk: List[str]) -> Dict[str, str]:
        try:
            got = _gemini_batch(chunk, language)
        except _Unavailable:
            return {}
        if got is None and len(chunk) > 1:            # malformed answer: split and retry the halves
            mid = len(chunk) // 2
            a, b = work(chunk[:mid]), work(chunk[mid:])
            a.update(b)
            return a
        if got is None:
            return {}
        out = {}
        for src, dst in zip(chunk, got):
            need = set(_PH.findall(src))
            # placeholders must survive and the answer must be in the target script
            if set(_PH.findall(dst)) == need and dst.strip() and right_script(dst, code):
                out[src] = dst.strip()
        return out

    chunks = [strings[i:i + 40] for i in range(0, len(strings), 40)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for part in pool.map(work, chunks):
            result.update(part)
    return result


def has_pending(code: Optional[str]) -> bool:
    return bool(code and _PENDING.get(code))


def flush(code: str) -> int:
    """Translates everything queued for this language, saves it, returns how many new translations were added."""
    pending = sorted(_PENDING.get(code, set()))
    if not pending:
        return 0
    _PENDING[code] = set()
    _ATTEMPTED.setdefault(code, set()).update(pending)      # never retry in a loop, even if some fail
    got = _translate_strings(pending, code)
    if got:
        _load(code).update(got)
        _save(code)
        _MEMO.clear()
    return len(got)


def seed(code: str, templates: Iterable[str]) -> int:
    """Pre-translates a list of templates (used offline to ship Marathi and Hindi)."""
    cache = _load(code)
    todo = [t for t in sorted(set(templates)) if t not in cache]
    added = 0
    for i in range(0, len(todo), 240):           # save as we go, so an interrupted run keeps its progress
        got = _translate_strings(todo[i:i + 240], code)
        if got:
            cache.update(got)
            _save(code)
            added += len(got)
    _MEMO.clear()
    return added


# ---------------------------------------------------------------------------
# patching Streamlit
# ---------------------------------------------------------------------------
def _current_code() -> Optional[str]:
    try:
        return code_for(st.session_state.get("selected_lang", "English"))
    except Exception:
        return None


# name -> (positional indexes (after self), keyword names) to translate
_TEXT_ARGS = {
    "markdown": ((0,), ("body", "help")), "caption": ((0,), ("body", "help")), "info": ((0,), ("body",)),
    "warning": ((0,), ("body",)), "success": ((0,), ("body",)), "error": ((0,), ("body",)), "title": ((0,), ("body",)),
    "header": ((0,), ("body",)), "subheader": ((0,), ("body",)), "toast": ((0,), ("body",)), "html": ((0,), ("body",)),
    "button": ((0,), ("label", "help")), "download_button": ((0,), ("label", "help")), "link_button": ((0,), ("label", "help")),
    "form_submit_button": ((0,), ("label", "help")), "expander": ((0,), ("label",)), "popover": ((0,), ("label", "help")),
    "tabs": ((0,), ("tabs",)), "checkbox": ((0,), ("label", "help")), "toggle": ((0,), ("label", "help")),
    "radio": ((0,), ("label", "help")), "selectbox": ((0,), ("label", "help", "placeholder")),
    "multiselect": ((0,), ("label", "help", "placeholder")), "text_input": ((0,), ("label", "help", "placeholder")),
    "text_area": ((0,), ("label", "help", "placeholder")), "number_input": ((0,), ("label", "help")),
    "slider": ((0,), ("label", "help")), "select_slider": ((0,), ("label", "help")), "date_input": ((0,), ("label", "help")),
    "file_uploader": ((0,), ("label", "help")), "metric": ((0,), ("label", "help")), "spinner": ((0,), ("text",)),
    "status": ((0,), ("label",)), "pills": ((0,), ("label",)), "segmented_control": ((0,), ("label",)),
    "audio_input": ((0,), ("label",)), "camera_input": ((0,), ("label",)),
}
_HAS_OPTIONS = {"selectbox", "radio", "multiselect", "select_slider", "pills", "segmented_control"}


def _wrap(orig, name: str, offset: int):
    positional, keywords = _TEXT_ARGS[name]

    @functools.wraps(orig)
    def wrapper(*args, **kw):
        code = _current_code()
        if kw.get("key") == "global_top_lang_selector":      # the language picker keeps its native names
            return orig(*args, **kw)
        if code or RECORD:
            args = list(args)
            for i in positional:
                if i + offset < len(args):
                    args[i + offset] = _any(args[i + offset], code)
            for k in keywords:
                if k in kw:
                    kw[k] = _any(kw[k], code)
            if name in _HAS_OPTIONS:
                base = kw.get("format_func") or str
                kw["format_func"] = lambda v, _b=base, _c=code: tr(_b(v), _c) if isinstance(_b(v), str) else _b(v)
        return orig(*args, **kw)
    return wrapper


def _wrap_write(orig, offset: int):
    @functools.wraps(orig)
    def wrapper(*args, **kw):
        code = _current_code()
        if code or RECORD:
            args = [(_any(a, code) if i >= offset else a) for i, a in enumerate(args)]
        return orig(*args, **kw)
    return wrapper


def _wrap_dataframe(orig, offset: int):
    @functools.wraps(orig)
    def wrapper(*args, **kw):
        code = _current_code()
        if code and len(args) > offset:
            try:
                import pandas as pd
                df = args[offset]
                if isinstance(df, pd.DataFrame):
                    df = df.rename(columns={c: tr(c, code) for c in df.columns if isinstance(c, str)})
                    args = list(args)
                    args[offset] = df
            except Exception:
                pass
        return orig(*args, **kw)
    return wrapper


def _wrap_plotly(orig, offset: int):
    @functools.wraps(orig)
    def wrapper(*args, **kw):
        code = _current_code()
        if code and len(args) > offset:
            try:
                import plotly.graph_objects as go
                fig = go.Figure(args[offset])
                lay = fig.layout
                if lay.title and lay.title.text:
                    lay.title.text = tr(lay.title.text, code)
                for ax in ("xaxis", "yaxis"):
                    a = getattr(lay, ax, None)
                    if a is not None and a.title and a.title.text:
                        a.title.text = tr(a.title.text, code)
                for tr_ in fig.data:
                    if getattr(tr_, "name", None):
                        tr_.name = tr(tr_.name, code)
                args = list(args)
                args[offset] = fig
            except Exception:
                pass
        return orig(*args, **kw)
    return wrapper


def install() -> None:
    """Wraps the Streamlit text-showing calls once per process (module functions and DeltaGenerator methods)."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    from streamlit.delta_generator import DeltaGenerator
    for name in _TEXT_ARGS:
        if hasattr(DeltaGenerator, name):
            setattr(DeltaGenerator, name, _wrap(getattr(DeltaGenerator, name), name, 1))
        if hasattr(st, name):
            setattr(st, name, _wrap(getattr(st, name), name, 0))
    if hasattr(DeltaGenerator, "write"):
        setattr(DeltaGenerator, "write", _wrap_write(DeltaGenerator.write, 1))
    st.write = _wrap_write(st.write, 0)
    if hasattr(DeltaGenerator, "dataframe"):
        setattr(DeltaGenerator, "dataframe", _wrap_dataframe(DeltaGenerator.dataframe, 1))
    st.dataframe = _wrap_dataframe(st.dataframe, 0)
    if hasattr(DeltaGenerator, "plotly_chart"):
        setattr(DeltaGenerator, "plotly_chart", _wrap_plotly(DeltaGenerator.plotly_chart, 1))
    st.plotly_chart = _wrap_plotly(st.plotly_chart, 0)


def finish_run() -> None:
    """Call at the end of a page run: translate what was missing and re-run once so the page shows it."""
    code = _current_code()
    if not has_pending(code):
        return
    with st.spinner(f"Translating to {LANGS.get(code, code)} (first time only)..."):
        added = flush(code)
    if added:
        st.rerun()
