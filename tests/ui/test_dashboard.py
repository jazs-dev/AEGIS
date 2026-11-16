from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_authenticated_dashboard_renders_controls_without_exception() -> None:
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run()
    app.text_input[0].input("astronauta")
    app.text_input[1].input("ISS-demo-2026")
    app.button[0].click().run()
    assert not app.exception
    assert len(app.selectbox) >= 1
    assert len(app.radio) >= 1
    assert any("Inicia una simulación" in item.value for item in app.info)


def test_dashboard_can_start_categorical_simulation_and_show_state() -> None:
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py")).run()
    app.text_input[0].input("astronauta")
    app.text_input[1].input("ISS-demo-2026")
    app.button[0].click().run()
    labels = [button.label for button in app.button]
    app.button[labels.index("Iniciar simulación")].click().run()
    assert not app.exception
    assert any("Estado efectivo" in metric.label for metric in app.metric)
