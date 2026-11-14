"""Configuración y control de acceso a las pantallas."""

import streamlit as st

from src.ui.theme import apply_theme
from src.ui.components.identity import render_identity
from src.ui.views.login import render_login
from src.ui.views.welcome import render_welcome


def main() -> None:
    st.set_page_config(page_title="AEGIS", layout="centered")
    apply_theme()
    render_identity()
    if st.session_state.get("authenticated", False):
        render_welcome()
    else:
        render_login()
