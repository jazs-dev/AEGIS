"""Identidad del sistema AEGIS."""

import streamlit as st


def _logout() -> None:
    for key in ("authenticated", "crew_username", "login_username", "login_password", "login_error"):
        st.session_state.pop(key, None)


def render_identity() -> None:
    left, right = st.columns([5, 1], vertical_alignment="center")
    with left:
        full_name = "<p>Autonomous Environmental &amp; General-health Integrated System</p>"
        st.html(f'<header class="aegis-identity"><h1>AEGIS</h1>{full_name}</header>')
    if st.session_state.get("authenticated", False):
        with right:
            st.container(horizontal=True, horizontal_alignment="right").button(
                "Log out",
                on_click=_logout
            )
    st.html('<div class="aegis-divider"></div>')
