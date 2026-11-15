from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.auth.service import authenticate


def test_configured_credentials_disable_demo(monkeypatch):
    monkeypatch.setenv("ISS_USERNAME", "pilot")
    monkeypatch.setenv("ISS_PASSWORD", "test-only-password")
    assert authenticate("pilot", "test-only-password")
    assert not authenticate("astronauta", "ISS-demo-2026")
    monkeypatch.delenv("ISS_PASSWORD")
    assert not authenticate("pilot", "")


def test_login_rejection_session_and_logout(monkeypatch):
    monkeypatch.delenv("ISS_USERNAME", raising=False)
    monkeypatch.delenv("ISS_PASSWORD", raising=False)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run()
    assert not app.exception
    app.text_input[0].input("astronauta")
    app.text_input[1].input("incorrecta")
    app.button[0].click().run()
    assert app.error
    assert app.error[0].value == "Incorrect username or password."
    assert len(app.text_input) == 2
    assert not app.success
    app.text_input[1].input("ISS-demo-2026")
    app.button[0].click().run()
    assert app.session_state["authenticated"]
    assert not app.text_input
    app.run()
    assert not app.exception
    app.button[0].click().run()
    assert len(app.text_input) == 2
    assert not app.exception
