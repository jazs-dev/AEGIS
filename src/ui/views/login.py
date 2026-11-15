"""Pantalla mínima de acceso al sistema."""

import streamlit as st

from src.auth.service import authenticate, demo_mode


def _submit_login() -> None:
    username = st.session_state.get("login_username", "")
    password = st.session_state.get("login_password", "")
    if authenticate(username, password):
        st.session_state["authenticated"] = True
        st.session_state["crew_username"] = username.strip()
        st.session_state.pop("login_error", None)
    else:
        st.session_state["login_error"] = "Incorrect username or password."
    st.session_state["login_password"] = ""


def render_login() -> None:
    st.html(
        """
        <style>
            .block-container { max-width: 540px; }

            /* Keep the login form clean: hide Streamlit's keyboard hint and
               the password visibility toggle. */
            div[data-testid="stForm"] [data-testid="InputInstructions"],
            div[data-testid="stForm"] button[aria-label="Show password"],
            div[data-testid="stForm"] button[aria-label="Hide password"] {
                display: none !important;
            }
        </style>
        """
    )
    with st.form("crew_login"):
        st.text_input("Username", key="login_username")
        st.text_input("Password", type="password", key="login_password")
        st.form_submit_button("Login", on_click=_submit_login, use_container_width=True)
    if st.session_state.get("login_error"):
        st.error(st.session_state["login_error"])
    if demo_mode():
        st.caption("Demo: astronaut / ISS-demo-2026")
