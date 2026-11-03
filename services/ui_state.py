"""
ui_state.py - keeps widget choices alive while their tab is hidden.

The navbar renders only the open tab (st.tabs(on_change="rerun") + tab.open), which is what makes the app
fast. Streamlit forgets the value of a widget that is not drawn in a run, so without this a farmer who
picks a river scenario, opens TODAY and comes back would find the choice reset (and the global river
banner would disappear). keep_widget_state() copies the values of the app's form widgets into a private
store each run and puts them back when their tab is closed.

Only plain values are kept (text, numbers, dates, option lists); buttons, toggles, uploads and editors
are never restored, because Streamlit does not allow setting them.
"""

import datetime as _dt
from typing import Iterable

import streamlit as st

_STORE = "_aa_sticky_widgets"
_PREFIXES = ("rw_", "mgmt_f_", "cb_", "dd_", "sm_", "qs_", "qw_", "bm_", "mcii_", "coc_", "leafvision_", "ai_")
_NEVER = {"dd_flash", "dd_farmer", "sm_my_ids", "dd_my_offers_by", "rw_csv_df", "qw_last"}
_SCALARS = (str, int, float, _dt.date, _dt.time)


def _restorable(v) -> bool:
    if isinstance(v, bool) or v is None:
        return False
    if isinstance(v, _SCALARS):
        return True
    if isinstance(v, (list, tuple)):
        return all(isinstance(x, _SCALARS) and not isinstance(x, bool) for x in v)
    return False


def keep_widget_state() -> None:
    """Call once near the top of every run, before any tab is drawn."""
    ss = st.session_state
    store = ss.get(_STORE)
    if store is None:
        store = {}
        ss[_STORE] = store
    for k in list(ss.keys()):
        if isinstance(k, str) and k.startswith(_PREFIXES) and k not in _NEVER:
            v = ss[k]
            if _restorable(v):
                store[k] = v
    for k, v in store.items():
        if k not in ss:
            try:
                ss[k] = v
            except Exception:
                pass


def forget(keys: Iterable[str]) -> None:
    """Drop widget values on purpose (for example when a form should reset to new defaults)."""
    store = st.session_state.get(_STORE, {})
    for k in keys:
        store.pop(k, None)
        if k in st.session_state:
            del st.session_state[k]
