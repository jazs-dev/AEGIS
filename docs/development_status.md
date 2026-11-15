# Estado de desarrollo

**Proyecto:** NASA Astronaut Health Monitor / AEGIS  
**Fecha de referencia:** 2026-11-15  
**Rama revisada:** `features/config`  
**Propósito:** establecer una referencia técnica antes de continuar el desarrollo.

## 1. Resumen ejecutivo

El repositorio contiene un prototipo funcional de interfaz Streamlit con autenticación local de demostración, un dashboard de monitoreo visual y documentación científica preliminar. La interfaz puede ejecutarse y las pruebas existentes pasan.

El procesamiento de señales, los algoritmos de clasificación y el monitoreo todavía no están implementados. Las carpetas `src/processing/`, `src/algorithms/` y `src/monitoring/` contienen únicamente sus archivos `__init__.py`.

Los archivos de configuración médica de `config/` todavía no son consumidos por el código. En esta etapa se normalizó su contrato interno y se añadió validación automatizada, pero la capa continúa siendo configuración de simulación y no un motor clínico validado.

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

### Separación prevista, todavía no implementada

La arquitectura documentada reserva responsabilidades independientes para:

- `src/processing/`: carga, validación, limpieza y transformación de señales.
- `src/algorithms/`: extracción de características, clasificación y detección de anomalías.
- `src/monitoring/`: evaluación de estados, reglas, alertas y trazabilidad.

Actualmente esas capas no tienen lógica funcional.

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
- Implementar carga y validación de configuraciones JSON.
- Integrar el esquema ya definido de `vf_transitions.json` en un cargador de configuración.
- Implementar procesamiento de señales en `src/processing/`.
- Implementar clasificación de variables en `src/algorithms/` usando las reglas de `config/`.
- Implementar la máquina de estados y las alertas en `src/monitoring/`.
- Conectar resultados de procesamiento y monitoreo con el dashboard.
- Incorporar datasets de prueba reproducibles.
- Agregar pruebas unitarias de configuración, procesamiento, reglas, transiciones y monitoreo.
- Definir criterios de calidad de señal, manejo de valores faltantes y trazabilidad de alertas.
- Validar científicamente cada regla antes de presentarla como resultado médico.

## 5. Pruebas y verificaciones

Comando ejecutado:

```bash
python -m pytest -q
```

Resultado observado:

```text
2 passed in 3.41s
```

Las pruebas actuales están en `tests/auth/test_login.py` y cubren:

- autenticación con credenciales configuradas;
- desactivación del modo demo cuando corresponde;
- rechazo de contraseña incorrecta;
- transición de sesión después de un login correcto;
- cierre de sesión.

Se añadieron pruebas de configuración en `tests/config/test_configuration.py`. Estas validan sintaxis JSON, categorías atómicas, referencias de variables, compatibilidad entre reglas y estados, prioridades y referencias de transiciones.

Todavía no existen pruebas para procesamiento, algoritmos, monitoreo o la interfaz completa.

También se verificó que Python puede importar directamente `src.ui.views.login` y que la instalación actual usa Python 3.12.15 y Streamlit 1.67.0.

## 6. Archivos de configuración

| Archivo | Estado | Uso observado |
|---|---|---|
| `config/classification_rules.json` | Nuevo, sin seguimiento Git | Reglas de clasificación de frecuencia cardiaca, SpO₂, frecuencia respiratoria y presión arterial |
| `config/ecg_classification.json` | Nuevo, sin seguimiento Git | Estados de calidad ECG, QRS y clasificación de ritmo |
| `config/fv_states.json` | Modificado localmente | Estados del modelo de monitorización de fibrilación ventricular |
| `config/variable_definitions.json` | Nuevo, sin seguimiento Git | Variables categóricas y valores permitidos |
| `config/vf_rules.json` | Nuevo, sin seguimiento Git | Reglas ordenadas para estados de fibrilación ventricular |
| `config/vf_transitions.json` | Configurado en esta etapa | Máquina de estados con prioridad, evaluación periódica, evaluación inmediata y salidas controladas de paro cardiaco |

Los archivos anteriores no son importados por ningún módulo de `src/` en el estado revisado. La validación automatizada solo verifica la capa declarativa; todavía no existe un evaluador Python.

El cambio local de `config/fv_states.json` se incorporó a la revisión de configuración. Se restauraron `responsiveness_status` y `breathing_status` como evidencia clínica explícita y atómica, y se añadió una versión de configuración. Esto no implica que el sistema pueda medirlos todavía.

### Inconsistencias corregidas

- `vf_transitions.json` dejó de contener texto de instrucciones y ahora es JSON válido.
- Los estados compuestos como `organized_or_abnormal`, `present_or_altered` y `absent_or_not_assessed` fueron reemplazados por categorías atómicas.
- Se añadieron explícitamente `responsiveness_status` y `breathing_status` para no confundir evidencia clínica de paro con una inferencia basada solo en ECG.
- Las reglas de FV mantienen la sospecha electrocardiográfica separada de la evidencia clínica de paro.
- La ausencia de presión arterial y una SpO₂ no fiable no son condiciones requeridas para sospechar FV ni se interpretan como ausencia de circulación.
- Las transiciones de salida de `VF_CARDIAC_ARREST` requieren control clínico externo y evaluación posterior; la normalización del ECG por sí sola no permite salir del estado.

## 7. Estado de Git

La rama actual es `features/config`.

El commit actual es:

```text
97b8f3b feat(login): alerta de usuario incorrecto y visualizacion de info
```

Commits recientes revisados:

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
 M config/fv_states.json
?? config/classification_rules.json
?? config/ecg_classification.json
?? config/variable_definitions.json
?? config/vf_rules.json
?? config/vf_transitions.json
?? docs/development_status.md
?? tests/config/
```

No se ejecutaron `git reset`, `git clean`, checkout destructivo, commit ni push.

## 8. Riesgos técnicos y dependencias

### Riesgos del código

- La lógica médica todavía no está separada en módulos ejecutables; las reglas JSON no tienen un evaluador.
- La señal ECG es sintética y no representa datos clínicos reales.
- Una lectura aislada no permite diagnosticar una condición médica.
- El estado `VF_CARDIAC_ARREST` no debe inferirse únicamente a partir del ECG; requiere información de pulso y evaluación clínica independiente.
- Las pruebas actuales validan consistencia estructural, pero no validan la corrección clínica de los criterios ECG.
- `vf_transitions.json` contiene un intervalo periódico de simulación, no un requisito de tiempo clínicamente validado.
- Las categorías `vf_compatible`, `normal_sinus` y `abnormal_non_vf` siguen dependiendo de algoritmos futuros y no tienen umbrales matemáticos definidos en la configuración.

### Riesgos de seguridad y operación

- Las credenciales demo están incorporadas en el código y se muestran en la pantalla.
- No existe bloqueo por intentos, recuperación de contraseña, proveedor de identidad ni sesión persistente.
- Las credenciales reales deben permanecer fuera del repositorio mediante variables de entorno.
- La configuración `runOnSave = true` y el file watcher automático pueden provocar recargas durante el desarrollo; el error de importación de Streamlit debe seguirse observando después de estabilizar el entorno.

### Dependencias

Las versiones están fijadas en `requirements.txt`. Entre las dependencias declaradas están Streamlit, NumPy, Pandas, SciPy, scikit-learn, Matplotlib y pytest. En el código actual se usan directamente Streamlit, NumPy, Pandas y pytest; las demás están preparadas para etapas posteriores o todavía no tienen consumidores.

## 9. Próximas etapas recomendadas

1. Revisar con el equipo el contenido y procedencia de todos los archivos de `config/`.
2. Implementar un cargador de configuración con errores explícitos.
3. Implementar primero funciones puras de clasificación de variables, sin importar Streamlit.
4. Implementar la evaluación de reglas y transiciones con casos de prueba.
5. Definir y validar matemáticamente los criterios de calidad ECG, QRS y ritmo.
6. Añadir procesamiento de ECG y validación de calidad de señal, manteniendo las limitaciones médicas documentadas.
7. Añadir una capa de monitoreo que produzca estados y alertas explicables.
8. Conectar el dashboard a resultados de monitoreo mediante una interfaz estable.
9. Añadir datasets de prueba y métricas de evaluación reproducibles.
10. Revisar dependencias y resolver el comportamiento de recarga de Streamlit antes de usar la aplicación como demostración estable.

## 10. Criterio de continuación

El siguiente cambio de implementación debería ser un componente independiente de carga y validación de configuración, acompañado de pruebas. No debería modificar todavía la interfaz ni interpretar datos médicos hasta que los criterios matemáticos ECG estén definidos y validados.

