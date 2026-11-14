"""Pantalla inicial protegida para comprobar el flujo de acceso."""

import streamlit as st


def _logout() -> None:
    for key in ("authenticated", "crew_username", "login_username", "login_password", "login_error"):
        st.session_state.pop(key, None)


def render_welcome() -> None:
    st.success(f"Sesión iniciada: {st.session_state['crew_username']}")
    st.write("El módulo de monitoreo se incorporará en la siguiente etapa.")
    st.button("Cerrar sesión", on_click=_logout)
