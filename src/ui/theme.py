"""Carga de recursos visuales locales."""

from pathlib import Path

import streamlit as st


def apply_theme() -> None:
    stylesheet = Path(__file__).resolve().parents[2] / "assets/styles/main.css"
    st.html(f"<style>{stylesheet.read_text(encoding='utf-8')}</style>")
