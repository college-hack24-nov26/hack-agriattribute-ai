"""Guards for app.py itself. Run: python -m pytest -q"""

import ast
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_no_bare_values_in_app():
    # Streamlit "magic" prints any bare value in the main script (a number, a ternary, a subscript) on the page.
    # Function calls and docstrings are fine; anything else is a leftover that would show up as stray text.
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    stray = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Expr):
            v = node.value
            if isinstance(v, (ast.Call, ast.Await)) or (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                continue
            stray.append(f"line {node.lineno}: {ast.get_source_segment(src, node)[:60]}")
    assert not stray, "bare values in app.py would be printed on the page:\n" + "\n".join(stray)


def test_magic_is_disabled():
    cfg = open(os.path.join(ROOT, ".streamlit", "config.toml"), encoding="utf-8").read()
    assert "magicEnabled = false" in cfg
