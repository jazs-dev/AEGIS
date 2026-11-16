"""Streamlit presentation for the application-independent monitoring pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from src.integration.monitoring_pipeline import MonitoringPipeline, PipelineMode
from src.simulation.physiological_simulator import SimulationConfig


SCENARIO_OPTIONS = ("NORMAL_MONITORING", "ABNORMAL_RHYTHM", "SUSPECTED_VF", "VF_CARDIAC_ARREST", "SIGNAL_INVALID")
MODE_OPTIONS: tuple[PipelineMode, ...] = ("categorical", "mathematical")


def _module_header(title: str) -> None:
    st.html(f'<div class="dashboard-module-header"><div><h2>{title}</h2></div></div>')


def _reading_card(label: str, value: object, unit: str, classification: str | None = None) -> None:
    st.metric(f"{label} ({unit})", "No disponible" if value is None else str(value))
    if classification:
        st.caption(f"Clasificación: {classification}")


def _measurement_value(result: Any, key: str) -> tuple[object, str]:
    if key == "blood_pressure":
        raw = result.sample.measurements
        value = None if raw.get("systolic_pressure") is None or raw.get("diastolic_pressure") is None else f"{raw['systolic_pressure']:.1f}/{raw['diastolic_pressure']:.1f}"
        return value, result.physiological_results["blood_pressure_status"].status
    raw = result.sample.measurements.get(key)
    variable = {"heart_rate": "heart_rate_status", "spo2": "spo2_status", "respiratory_rate": "respiratory_rate_status"}.get(key)
    classification = result.physiological_results[variable].status if variable else "simulated"
    return raw, classification if raw is not None else "not_assessed"


def _render_controls() -> MonitoringPipeline | None:
    st.subheader("Simulación reproducible")
    scenario = st.selectbox("Escenario", SCENARIO_OPTIONS, key="dashboard_scenario")
    mode = st.radio(
        "Modalidad",
        MODE_OPTIONS,
        format_func=lambda value: "Simulación categórica" if value == "categorical" else "Análisis ECG experimental",
        key="dashboard_mode",
        horizontal=True,
    )
    seed = st.number_input("Semilla", min_value=0, value=0, step=1, key="dashboard_seed")
    duration = st.number_input("Duración (s)", min_value=1.0, value=5.0, step=1.0, key="dashboard_duration")
    interval = st.number_input("Intervalo (s)", min_value=0.1, value=1.0, step=0.1, key="dashboard_interval")
    start = st.button("Iniciar simulación", type="primary")
    advance = st.button("Avanzar muestra")
    run_all = st.button("Ejecutar restante")
    reset = st.button("Reiniciar sesión")

    if start:
        pipeline = MonitoringPipeline(
            simulation=SimulationConfig(
                scenario=scenario,
                duration_seconds=float(duration),
                interval_seconds=float(interval),
                seed=int(seed),
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            mode=mode,
        )
        st.session_state["monitoring_pipeline"] = pipeline
        pipeline.step()
    pipeline = st.session_state.get("monitoring_pipeline")
    if reset and pipeline is not None:
        pipeline.reset()
    if pipeline is not None and advance:
        pipeline.step()
    if pipeline is not None and run_all:
        pipeline.run_all()
    return pipeline


def _render_state(result: Any) -> None:
    monitor = result.monitor_result
    st.subheader("Estado del monitoreo")
    st.caption(result.modality_label)
    st.metric("Estado efectivo", monitor.effective_state)
    st.write(f"Estado candidato: `{monitor.candidate_state or 'indeterminado'}`")
    st.write(f"Evaluación: `{monitor.evaluation_mode}`")
    if monitor.transition is not None:
        if monitor.transition.allowed:
            st.success(f"Transición {monitor.transition.transition_id} permitida: {monitor.transition.reason}")
        else:
            st.warning(f"Transición rechazada: {monitor.transition.reason}")
    if monitor.rule_decision is not None:
        decision = monitor.rule_decision
        st.write(f"Regla: `{decision.rule_id or 'ninguna'}` · prioridad: `{decision.priority or '—'}`")
        if decision.missing_evidence:
            st.warning(f"Evidencia faltante: {', '.join(decision.missing_evidence)}")
        if decision.evaluation_status == "indeterminate":
            st.warning("La evaluación es indeterminada; no se presenta como monitoreo normal.")


def _render_health(result: Any) -> None:
    st.subheader("Indicadores fisiológicos")
    first = st.columns(3)
    for column, label, key, unit in zip(first, ("Frecuencia cardiaca", "SpO₂", "Frecuencia respiratoria"), ("heart_rate", "spo2", "respiratory_rate"), ("bpm", "%", "resp/min")):
        with column:
            value, classification = _measurement_value(result, key)
            _reading_card(label, value, unit, classification)
    second = st.columns(2)
    for column, label, key, unit in zip(second, ("Presión arterial", "Temperatura corporal"), ("blood_pressure", "body_temperature"), ("mmHg", "°C")):
        with column:
            value, classification = _measurement_value(result, key)
            _reading_card(label, value, unit, classification)


def _render_ecg(result: Any) -> None:
    st.subheader("ECG")
    analysis = result.ecg_analysis
    if analysis is None:
        st.info("No existen muestras ECG en la modalidad categórica; las categorías fueron entradas sintéticas del simulador.")
        return
    ecg = analysis.signal
    samples = ecg.samples
    time = np.arange(samples.size) / ecg.sampling_rate_hz
    chart = pd.DataFrame({f"ECG ({ecg.amplitude_unit})": samples}, index=time)
    if analysis.qrs and analysis.qrs.positions:
        markers = np.full(samples.size, np.nan)
        positions = np.asarray(analysis.qrs.positions)
        positions = positions[positions < samples.size]
        markers[positions] = samples[positions]
        chart["QRS"] = markers
    st.line_chart(chart, height=260, width="stretch")
    st.caption(f"{ecg.record_id} · {ecg.sampling_rate_hz:g} Hz · ventana {samples.size / ecg.sampling_rate_hz:.2f} s · {ecg.source}")
    rhythm = analysis.rhythm.rhythm_classification if analysis.rhythm else "not_assessed"
    quality = analysis.rhythm.ecg_quality if analysis.rhythm else analysis.processed.ecg_quality
    qrs = analysis.qrs.qrs_status if analysis.qrs else "not_assessed"
    st.write(f"Calidad: `{quality}` · QRS: `{qrs}` · Ritmo: `{rhythm}`")
    if analysis.processed.features:
        with st.expander("Características calculadas"):
            st.json({key: round(value, 6) if np.isfinite(value) else None for key, value in analysis.processed.features.items()})


def _render_history(pipeline: MonitoringPipeline) -> None:
    st.subheader("Historial temporal")
    if not pipeline.history:
        st.info("Aún no hay evaluaciones.")
        return
    rows = []
    for item in pipeline.history:
        monitor = item.monitor_result
        transition = monitor.transition
        rows.append({
            "timestamp": monitor.timestamp,
            "estado anterior": transition.previous_state if transition else "—",
            "candidato": monitor.candidate_state or "indeterminado",
            "efectivo": monitor.effective_state,
            "regla": monitor.rule_decision.rule_id if monitor.rule_decision else "—",
            "evaluación": monitor.evaluation_mode,
            "transición": transition.transition_id if transition and transition.allowed else "rechazada",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_dashboard() -> None:
    pipeline = _render_controls()
    if pipeline is None or pipeline.current is None:
        st.info("Inicia una simulación para comenzar. El reinicio solo reinicia la demostración, no representa recuperación clínica.")
        return
    result = pipeline.current
    left, right = st.columns([2, 3], gap="small")
    with left:
        with st.container(border=True, key="health_panel"):
            _module_header("HEALTH MONITOR")
            _render_health(result)
            _render_state(result)
    with right:
        with st.container(border=True, key="medical_panel"):
            _module_header("SIGNAL ANALYSIS")
            _render_ecg(result)
            _render_history(pipeline)
