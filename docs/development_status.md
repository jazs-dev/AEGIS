# Estado de desarrollo

**Proyecto:** NASA Astronaut Health Monitor / AEGIS  
**Fecha de referencia:** 2026-11-15  
**Rama revisada:** `features/physiological-simulation`
**Propósito:** establecer una referencia técnica antes de continuar el desarrollo.

## 1. Resumen ejecutivo

El repositorio contiene un prototipo funcional de interfaz Streamlit con autenticación local de demostración, un dashboard de monitoreo visual y documentación científica preliminar. La interfaz puede ejecutarse y las pruebas existentes pasan.

La primera capa de procesamiento fisiológico, el motor determinista de reglas, la máquina de estados, el coordinador de monitoreo y un simulador reproducible ya están implementados sin dependencia de Streamlit. El procesamiento ECG, la detección matemática de FV y la integración con el dashboard todavía no están implementados.

Los archivos de configuración médica de `config/` son cargados por el procesamiento y el monitoreo. La capa continúa siendo configuración de simulación y no un motor clínico validado.

## 2. Arquitectura implementada

### Entrada

- `app.py` importa `main` desde `src.ui.application` y lo ejecuta.
- No contiene lógica de negocio.

### Autenticación

- `src/auth/service.py` contiene `demo_mode()` y `authenticate()`.
- Usa `ISS_USERNAME` y `ISS_PASSWORD` cuando ambas variables están definidas.
- Si no hay credenciales configuradas, activa el modo demo local.
- Utiliza `hmac.compare_digest()` para comparar las credenciales.

### Interfaz

- `src/ui/application.py` configura Streamlit, aplica el tema, muestra la identidad y decide entre login y dashboard.
- `src/ui/theme.py` carga `assets/styles/main.css`.
- `src/ui/components/identity.py` muestra el encabezado AEGIS y el cierre de sesión.
- `src/ui/views/login.py` implementa el formulario de acceso y los mensajes de error.
- `src/ui/views/dashboard.py` muestra tarjetas fisiológicas, un ECG simulado y un panel de estado.

### Configuración visual

- `.streamlit/config.toml` define el tema oscuro, el modo de toolbar y el comportamiento del file watcher.
- `assets/styles/main.css` contiene los estilos de la interfaz.

### Separación prevista, parcialmente implementada

La arquitectura documentada reserva responsabilidades independientes para:

- `src/processing/`: carga de configuración y validación/clasificación de mediciones fisiológicas; el procesamiento ECG aún está pendiente.
- `src/algorithms/`: extracción de características, clasificación y detección de anomalías.
- `src/monitoring/`: evaluación de estados, reglas, alertas y trazabilidad.

`src/algorithms/` todavía no tiene lógica funcional. `src/processing/` y `src/monitoring/` cuentan con las capas descritas a continuación.

### Procesamiento fisiológico implementado

- `src/processing/config_loader.py` localiza, carga y valida los seis JSON sin depender del directorio de ejecución ni de Streamlit.
- `src/processing/measurement_validator.py` valida tipo numérico, finitud, unidades opcionales, disponibilidad, dominios configurados y consistencia sistólica/diastólica.
- `src/processing/variable_classifier.py` evalúa de forma restringida las expresiones numéricas de `classification_rules.json` y produce categorías atómicas.

La salida incluye variable, valor original, unidad, categoría, validez, regla coincidente y explicación. La validez distingue `valid`, `not_assessed`, `invalid` y `out_of_domain`.

### Motor de decisiones implementado

- `src/monitoring/rule_engine.py` evalúa las reglas `R01` a `R05` por prioridad, distingue `matched`, `no_match` e `indeterminate`, y conserva una traza de condiciones.
- `src/monitoring/state_machine.py` aplica las transiciones `T01` a `T10`, conserva el estado efectivo y bloquea salidas de `VF_CARDIAC_ARREST` sin autorización y reevaluación.
- `src/monitoring/monitor.py` coordina regla, transición, modo periódico/inmediato, timestamps externos e historial.
- `src/simulation/physiological_simulator.py` genera mediciones, categorías ECG/clínicas sintéticas y secuencias reproducibles que alimentan el monitor existente.

El monitor separa `candidate_state` de `effective_state`. Una entrada sin evidencia suficiente no inventa un estado: conserva el estado efectivo y registra la evaluación indeterminada.

## 3. Funcionalidades disponibles

- Arranque mediante Streamlit desde la raíz del proyecto.
- Configuración visual local sin recursos externos.
- Login de demostración con usuario `astronauta` y contraseña `ISS-demo-2026` cuando no existen credenciales de entorno.
- Login con credenciales locales mediante `ISS_USERNAME` e `ISS_PASSWORD`.
- Rechazo de credenciales incorrectas.
- Estado de sesión autenticada en `st.session_state`.
- Cierre de sesión.
- Dashboard protegido por autenticación.
- Tarjetas visuales para frecuencia cardiaca, SpO₂, frecuencia respiratoria, temperatura y presión arterial.
- ECG sintético claramente marcado como señal simulada.
- Panel de estado del asistente médico en modo placeholder.

Estas funciones constituyen una demostración de interfaz; no equivalen a monitorización clínica ni a diagnóstico.

## 4. Módulos pendientes

- Definir una API interna para lecturas fisiológicas y señales ECG.
- Integrar el cargador de configuración y la clasificación fisiológica con una fuente de mediciones o dataset reproducible.
- Implementar procesamiento ECG y extracción de características en `src/processing/` y `src/algorithms/`.
- Integrar el simulador con datasets o fuentes de mediciones externas cuando estén disponibles.
- Conectar resultados de procesamiento y monitoreo con el dashboard.
- Incorporar datasets de prueba reproducibles.
- Agregar pruebas unitarias de ECG, reglas, transiciones y monitoreo.
- Definir criterios de calidad de señal, manejo de valores faltantes y trazabilidad de alertas.
- Validar científicamente cada regla antes de presentarla como resultado médico.

## 5. Pruebas y verificaciones

Comando ejecutado:

```bash
python -m pytest -q
```

Resultado observado:

```text
80 passed in 3.27s
```

Las pruebas actuales están en `tests/auth/test_login.py` y cubren:

- autenticación con credenciales configuradas;
- desactivación del modo demo cuando corresponde;
- rechazo de contraseña incorrecta;
- transición de sesión después de un login correcto;
- cierre de sesión.

Se añadieron pruebas de configuración en `tests/config/test_configuration.py`. Estas validan sintaxis JSON, categorías atómicas, referencias de variables, compatibilidad entre reglas y estados, prioridades y referencias de transiciones.

La documentación arquitectónica se amplió en `docs/architecture.md` con el flujo híbrido, contratos de datos, responsabilidades por capa, límites del procesamiento ECG y cuatro diagramas Mermaid.

Las pruebas nuevas en `tests/processing/test_processing.py` cubren límites inclusivos y exclusivos, valores normales, valores faltantes, tipos incorrectos, `NaN`, infinitos, unidades incompatibles, dominios inválidos, presión sistólica menor que diastólica, expresiones mal formadas, reglas ambiguas y archivos de configuración faltantes o inválidos.

Las pruebas nuevas en `tests/monitoring/test_monitoring.py` cubren los cinco estados, prioridad de paro sobre sospecha, evidencia faltante, categorías desconocidas, transiciones permitidas y prohibidas, retención de paro, salida autorizada, historial, intervalo periódico y evaluación inmediata.

Las pruebas nuevas en `tests/simulation/test_physiological_simulator.py` cubren reproducibilidad por semilla, variación entre semillas, los cinco escenarios, mediciones faltantes e inválidas, integración con procesamiento y monitoreo, transiciones permitidas y rechazadas, retención de paro, controles externos explícitos y trazabilidad de muestras.

Todavía no existen pruebas para procesamiento ECG, algoritmos matemáticos de ritmo o la integración con la interfaz completa.

También se verificó que Python puede importar directamente `src.ui.views.login` y que la instalación actual usa Python 3.12.15 y Streamlit 1.67.0.

## 6. Archivos de configuración

| Archivo | Estado | Uso observado |
|---|---|---|
| `config/classification_rules.json` | Versionado en la base | Reglas de clasificación de frecuencia cardiaca, SpO₂, frecuencia respiratoria y presión arterial |
| `config/ecg_classification.json` | Versionado en la base | Estados de calidad ECG, QRS y clasificación de ritmo |
| `config/fv_states.json` | Versionado en la base | Estados del modelo de monitorización de fibrilación ventricular |
| `config/variable_definitions.json` | Versionado en la base | Variables categóricas y valores permitidos |
| `config/vf_rules.json` | Versionado en la base | Reglas ordenadas para estados de fibrilación ventricular |
| `config/vf_transitions.json` | Configurado en esta etapa | Máquina de estados con prioridad, evaluación periódica, evaluación inmediata y salidas controladas de paro cardiaco |

Los archivos anteriores son cargados y validados por `src/processing/config_loader.py`; `vf_rules.json` y `vf_transitions.json` son interpretados por `src/monitoring/`. La validación no constituye validación clínica.

Los seis JSON forman parte de la base validada de la rama. `responsiveness_status` y `breathing_status` se reciben como categorías clínicas explícitas; el sistema todavía no adquiere automáticamente esas evidencias.

### Inconsistencias corregidas

- `vf_transitions.json` dejó de contener texto de instrucciones y ahora es JSON válido.
- Los estados compuestos como `organized_or_abnormal`, `present_or_altered` y `absent_or_not_assessed` fueron reemplazados por categorías atómicas.
- Se añadieron explícitamente `responsiveness_status` y `breathing_status` para no confundir evidencia clínica de paro con una inferencia basada solo en ECG.
- Las reglas de FV mantienen la sospecha electrocardiográfica separada de la evidencia clínica de paro.
- La ausencia de presión arterial y una SpO₂ no fiable no son condiciones requeridas para sospechar FV ni se interpretan como ausencia de circulación.
- Las transiciones de salida de `VF_CARDIAC_ARREST` requieren control clínico externo y evaluación posterior; la normalización del ECG por sí sola no permite salir del estado.

## 7. Estado de Git

La rama actual es `features/physiological-simulation`, creada desde el `HEAD` validado de `features/vf-decision-engine`.

El commit base de la rama es:

```text
068fdeb feat(monitoring): implement VF rule engine and state machine
```

Commits recientes revisados:

- `505835e` — clasificación fisiológica determinista.
- `068fdeb` — motor de reglas, máquina de estados y monitor.
- `6b9af54` — documentación de la arquitectura determinista.
- `e442ec7` — configuración y validación de monitorización FV.

- `97b8f3b` — alerta de usuario incorrecto y visualización de información.
- `ec184a5` — estados de fibrilación ventricular.
- `2e2447a` — implementación inicial del dashboard.
- `fb5a907` — estructura inicial del login AEGIS.
- `dff3f60` — documentación científica inicial.
- `539503a` — configuración inicial del proyecto.
- `423076d` — commit inicial.

Remoto configurado:

```text
origin https://github.com/jazs-dev/AEGIS.git
```

Estado local pendiente al finalizar esta etapa:

```text
 M docs/architecture.md
 M docs/development_status.md
?? src/simulation/
?? tests/simulation/
```

No se ejecutaron `git reset`, `git clean`, checkout destructivo, commit ni push.

## 8. Riesgos técnicos y dependencias

### Riesgos del código

- Las reglas ECG todavía dependen de un clasificador de señal no implementado; el motor de reglas y la máquina de estados ya evalúan las categorías recibidas.
- La señal ECG es sintética y no representa datos clínicos reales.
- Una lectura aislada no permite diagnosticar una condición médica.
- El estado `VF_CARDIAC_ARREST` no debe inferirse únicamente a partir del ECG; requiere información de pulso y evaluación clínica independiente.
- Las pruebas actuales validan consistencia estructural, pero no validan la corrección clínica de los criterios ECG.
- `vf_transitions.json` contiene un intervalo periódico de simulación, no un requisito de tiempo clínicamente validado.
- Las categorías `vf_compatible`, `normal_sinus` y `abnormal_non_vf` siguen dependiendo de algoritmos futuros y no tienen umbrales matemáticos definidos en la configuración.
- El clasificador actual solo procesa frecuencia cardiaca, SpO₂, frecuencia respiratoria y presión arterial; no interpreta ECG ni categorías clínicas de pulso, respuesta o respiración.
- Los valores negativos de frecuencia cardiaca, SpO₂ y frecuencia respiratoria se marcan `out_of_domain` conforme al dominio explícito de la configuración; no se agregaron límites clínicos superiores no definidos.
- La regla de presión arterial `altered` funciona como fallback cuando no coincide `low`, `stable` o `elevated`; la semántica clínica de ese fallback requiere validación posterior.
- La expresión de bradicardia (`<60`) se solapa matemáticamente con la expresión de frecuencia cardiaca inválida (`<0`). El validador resuelve primero el dominio de entrada y marca valores negativos como `out_of_domain`, evitando una coincidencia ambigua sin modificar el JSON.
- La categoría `invalid` de presión arterial existe en `variable_definitions.json`, pero no tiene una regla numérica específica en `classification_rules.json`; se utiliza únicamente cuando la validación detecta tipo, finitud, unidad o consistencia inválida.
- `vf_transitions.json` no permite `NORMAL_MONITORING → ABNORMAL_RHYTHM`; `T04` solo parte de `SIGNAL_INVALID` o `SUSPECTED_VF`. La simulación conserva esta restricción y registra cualquier intento rechazado.

### Riesgos de seguridad y operación

- Las credenciales demo están incorporadas en el código y se muestran en la pantalla.
- No existe bloqueo por intentos, recuperación de contraseña, proveedor de identidad ni sesión persistente.
- Las credenciales reales deben permanecer fuera del repositorio mediante variables de entorno.
- La configuración `runOnSave = true` y el file watcher automático pueden provocar recargas durante el desarrollo; el error de importación de Streamlit debe seguirse observando después de estabilizar el entorno.

### Dependencias

Las versiones están fijadas en `requirements.txt`. Entre las dependencias declaradas están Streamlit, NumPy, Pandas, SciPy, scikit-learn, Matplotlib y pytest. En el código actual se usan directamente Streamlit, NumPy, Pandas y pytest; las demás están preparadas para etapas posteriores o todavía no tienen consumidores.

## 9. Próximas etapas recomendadas

1. Integrar `src/simulation/` con datasets o fuentes de mediciones reproducibles adicionales.
2. Definir y validar matemáticamente los criterios de calidad ECG, QRS y ritmo.
3. Añadir procesamiento ECG y extracción de características, manteniendo las limitaciones documentadas.
4. Revisar si debe autorizarse explícitamente la transición `NORMAL_MONITORING → ABNORMAL_RHYTHM` en una futura versión de configuración.
5. Definir la presentación de alertas experimentales y sus limitaciones.
6. Conectar el dashboard a resultados de monitoreo mediante una interfaz estable.
7. Añadir datasets de evaluación y métricas reproducibles.
8. Revisar dependencias y resolver el comportamiento de recarga de Streamlit antes de usar la aplicación como demostración estable.

## 10. Procesamiento ECG experimental implementado

En `features/ecg-vf-detection` se añadieron `src/processing/ecg_processing.py`, `src/algorithms/qrs_detection.py`, `src/algorithms/vf_detection.py` y `config/ecg_algorithm_parameters.json`. El flujo probado es:

```text
ECGSignal -> process_ecg -> detect_qrs -> classify_ecg
          -> categorias ECG -> Monitor -> reglas -> maquina de estados
```

Las pruebas cubren señales organizadas, actividad desorganizada sintética, constantes, cortas, valores faltantes, saturación, reproducibilidad, intervalos RR e integración con `Monitor`. La ausencia de QRS en una señal sin actividad no activa `vf_compatible`.

Los cortes `0.5–30 Hz` para análisis, `5–15 Hz` para QRS, ventana de 4 s, límites de calidad, pesos y umbrales espectrales son valores de ingeniería para desarrollo sintético. No son umbrales diagnósticos y requieren calibración independiente. `ecg_classification.json` no se modificó.

`normal_sinus` es una categoría conservadora de software basada en QRS organizado y regularidad, no una demostración clínica de ritmo sinusal. `vf_compatible` describe únicamente compatibilidad con el método experimental. `VF_CARDIAC_ARREST` sigue dependiendo de pulso, respuesta y respiración independientes.

No se implementó aún un cargador WFDB ni se reportaron métricas sobre registros reales. Las fuentes candidatas son CUDB y MIT-BIH Malignant Ventricular Ectopy. La transición `NORMAL_MONITORING → ABNORMAL_RHYTHM` continúa rechazada por configuración y no fue alterada automáticamente.

## 11. Integración Streamlit implementada

Se añadió `src/integration/monitoring_pipeline.py` y se actualizó `src/ui/views/dashboard.py`. El pipeline conserva la separación entre presentación y lógica: la vista controla escenario, modalidad, semilla, duración e intervalo; el pipeline reutiliza el simulador, clasificadores, procesamiento ECG, motor de reglas y máquina de estados.

La modalidad categórica conserva las categorías ECG simuladas y está rotulada como demostración sin detección matemática. La modalidad matemática genera una forma sintética separada, procesa las mismas muestras que se grafican y obtiene `ecg_quality`, `qrs_status` y `rhythm_classification` del detector. La etiqueta del escenario y `expected_state_oracle` no deciden el resultado.

El dashboard muestra indicadores fisiológicos con clasificación, ECG y QRS cuando existen muestras, características calculadas, estado candidato, estado efectivo, reglas, transiciones rechazadas, evidencia faltante e historial temporal. La autenticación permanece sin cambios.

Las pruebas de integración y UI verifican las dos modalidades, la independencia de la capa de integración respecto de Streamlit, la persistencia de sesión, el historial, la retención de paro y el manejo de señal inválida. El sistema sigue siendo `simulation_only` y no constituye validación clínica.

## 12. Criterio de continuación

El siguiente cambio debería integrar una ruta WFDB reproducible, separar desarrollo/evaluación por registro, calibrar los parámetros experimentales y revisar resultados con especialistas. No debe presentar `vf_compatible` como diagnóstico clínico.

## 13. Evaluación baseline de FV

Se añadieron `src/datasets/physionet_loader.py`, `src/datasets/rhythm_annotations.py`, `src/evaluation/ecg_segmentation.py`, `src/evaluation/vf_evaluator.py`, `src/evaluation/reporting.py`, `scripts/evaluate_vf.py` y `docs/vf_validation_protocol.md`. El baseline conserva la configuración ECG versión `0.1.0` sin modificar umbrales.

El cargador soporta archivos WFDB locales y registros remotos de CUDB/VFDB cuando hay conectividad. La evaluación usa ventanas completas de 4 segundos, separa `VF`, `NON_VF`, `AMBIGUOUS` y `EXCLUDED`, calcula cobertura y conserva resultados por segmento, registro, dataset, ritmo y calidad.

El informe también resume episodios temporales: inicio anotado, primera detección disponible al final de una ventana, retardo aproximado, episodios no detectados y falsas alarmas fuera de FV.

En este entorno no se pudieron descargar registros reales porque falló la resolución DNS hacia `physionet.org`. No se han generado métricas reales ni se presentan resultados inventados. Las pruebas usan fixtures WFDB sintéticos pequeños para validar lectura, anotaciones, segmentación, métricas, reportes y conexión con el detector.

Posteriormente se utilizó el endpoint S3 público oficial de PhysioNet. Se evaluaron seis registros reales (VFDB `422`, `424`, `426`, `430`; CUDB `cu01`, `cu03`) con checksums oficiales verificados. El resultado global fue TP=445, FP=290, TN=1008, FN=197, sensibilidad=0.6931, especificidad=0.7766, precisión=0.6054, F1=0.6463 y 90 abstenciones sobre 2,030 ventanas binarias. El informe y las figuras están en `docs/vf_baseline_results.md` y `data/processed/vf_evaluation/combined_baseline_20261115_with_examples/`. Es un baseline preliminar, no validación clínica.

