# Estado de desarrollo

**Proyecto:** NASA Astronaut Health Monitor / AEGIS  
**Fecha de referencia:** 2026-11-15  
**Rama revisada:** `features/vf-decision-engine`
**Propósito:** establecer una referencia técnica antes de continuar el desarrollo.

## 1. Resumen ejecutivo

El repositorio contiene un prototipo funcional de interfaz Streamlit con autenticación local de demostración, un dashboard de monitoreo visual y documentación científica preliminar. La interfaz puede ejecutarse y las pruebas existentes pasan.

La primera capa de procesamiento fisiológico, el motor determinista de reglas, la máquina de estados y el coordinador de monitoreo ya están implementados sin dependencia de Streamlit. El procesamiento ECG, la detección matemática de FV y la integración con el dashboard todavía no están implementados.

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
62 passed in 3.30s
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

La rama actual es `features/vf-decision-engine`, creada desde el `HEAD` validado de `features/physiological-processing`.

El commit base de la rama es:

```text
505835e feat(processing): implement deterministic physiological classification
```

Commits recientes revisados:

- `505835e` — clasificación fisiológica determinista.
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
?? src/monitoring/monitor.py
?? src/monitoring/rule_engine.py
?? src/monitoring/state_machine.py
?? tests/monitoring/
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

### Riesgos de seguridad y operación

- Las credenciales demo están incorporadas en el código y se muestran en la pantalla.
- No existe bloqueo por intentos, recuperación de contraseña, proveedor de identidad ni sesión persistente.
- Las credenciales reales deben permanecer fuera del repositorio mediante variables de entorno.
- La configuración `runOnSave = true` y el file watcher automático pueden provocar recargas durante el desarrollo; el error de importación de Streamlit debe seguirse observando después de estabilizar el entorno.

### Dependencias

Las versiones están fijadas en `requirements.txt`. Entre las dependencias declaradas están Streamlit, NumPy, Pandas, SciPy, scikit-learn, Matplotlib y pytest. En el código actual se usan directamente Streamlit, NumPy, Pandas y pytest; las demás están preparadas para etapas posteriores o todavía no tienen consumidores.

## 9. Próximas etapas recomendadas

1. Integrar `src/processing/` con una fuente de mediciones o dataset reproducible.
2. Definir y validar matemáticamente los criterios de calidad ECG, QRS y ritmo.
3. Añadir procesamiento ECG y extracción de características, manteniendo las limitaciones documentadas.
4. Definir la presentación de alertas experimentales y sus limitaciones.
5. Conectar el dashboard a resultados de monitoreo mediante una interfaz estable.
6. Añadir datasets de prueba y métricas de evaluación reproducibles.
7. Revisar dependencias y resolver el comportamiento de recarga de Streamlit antes de usar la aplicación como demostración estable.

## 10. Criterio de continuación

El siguiente cambio de implementación debería definir y validar matemáticamente la calidad ECG, QRS y ritmo. No debería modificar todavía la interfaz ni implementar detección de FV hasta que existan criterios reproducibles y datasets de evaluación.

