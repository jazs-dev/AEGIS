"""Identidad del sistema AEGIS."""

import streamlit as st


def render_identity() -> None:
    st.html('''<header class="aegis-identity">
        <h1>AEGIS</h1>
        <p>Autonomous Environmental &amp; General-health Integrated System</p>
    </header>''')
