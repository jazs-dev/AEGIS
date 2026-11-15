import streamlit as st
import numpy as np
import pandas as pd


PHYSIOLOGICAL_READINGS = {
    "heart_rate": None,
    "spo2": None,
    "respiratory_rate": None,
    "body_temperature": None,
    "blood_pressure": None,
}


def _module_header(title: str) -> None:
    st.html(f'''<div class="dashboard-module-header">
        <div><h2>{title}</h2>
    </div>''')


def _reading_value(value: object, unit: str = "") -> str:
    return f"—{unit}" if value is None else f"{value}{unit}"


def _reading_card(label: str, value: object, unit: str) -> None:
    display_value = "—" if value is None else value
    st.html(f'''<div class="reading-card">
        <div class="reading-label">{label}</div>
        <div class="reading-value">{display_value}<span class="reading-unit">{unit}</span></div>
    </div>''')


def _simulated_ecg(samples: int = 400, sample_rate: int = 100) -> pd.DataFrame:
    """Create a visual-only ECG-like signal until a dataset is connected."""
    time = np.arange(samples) / sample_rate
    phase = (time * 1.2) % 1
    signal = 0.02 * np.sin(2 * np.pi * 8 * time)
    signal += 0.08 * np.exp(-((phase - 0.18) / 0.035) ** 2)
    signal -= 0.12 * np.exp(-((phase - 0.46) / 0.012) ** 2)
    signal += 1.0 * np.exp(-((phase - 0.50) / 0.018) ** 2)
    signal -= 0.25 * np.exp(-((phase - 0.54) / 0.015) ** 2)
    signal += 0.18 * np.exp(-((phase - 0.72) / 0.08) ** 2)
    return pd.DataFrame({"ECG (mV)": signal}, index=time)


def render_ecg_chart(ecg_data: pd.DataFrame | None = None) -> None:
    """Render ECG data supplied by a dataset or a clearly marked demo signal."""
    chart_data = ecg_data if ecg_data is not None else _simulated_ecg()
    st.markdown("**ECG**")
    st.line_chart(chart_data, height=170, use_container_width=True)
    if ecg_data is None:
        st.caption("Simulated signal · placeholder for dataset integration")


def render_health_monitor(readings: dict | None = None) -> None:
    """Render physiological indicators; readings can later come from a data source."""
    values = {**PHYSIOLOGICAL_READINGS, **(readings or {})}
    first_row = st.columns(3, gap="small")
    with first_row[0]:
        _reading_card("Heart Rate", values["heart_rate"], "bpm")
    with first_row[1]:
        _reading_card("SpO₂", values["spo2"], "%")
    with first_row[2]:
        _reading_card("Respiratory Rate", values["respiratory_rate"], "breaths/min")

    second_row = st.columns(2, gap="small")
    with second_row[0]:
        _reading_card("Body Temperature", values["body_temperature"], "°C")
    with second_row[1]:
        _reading_card("Blood Pressure", values["blood_pressure"], "mmHg")

    _reading_card("ECG", "READY", "mV")
    render_ecg_chart()


def render_medical_assistant() -> None:
    """Render one automatic status console for future assistant events."""
    st.html('''<div class="status-console">
        <div class="status-console-title">SYSTEM STATUS</div>
        <pre>&gt; MEDICAL ASSISTANT / ONLINE
&gt; WAITING FOR EVENTS...</pre>
    </div>''')


def render_dashboard() -> None:

    left, right = st.columns([2, 3], gap="small")
    with left:
        with st.container(border=True, key="health_panel"):
            _module_header(
                "HEALTH MONITOR",
            )
            render_health_monitor()
    with right:
        with st.container(border=True, key="medical_panel"):
            _module_header(
                "MEDICAL ASSISTANT",
            )
            render_medical_assistant()

