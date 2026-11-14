# Catálogo de condiciones médicas

**Proyecto:** NASA Astronaut Health Monitor  
**Estado:** Investigación en desarrollo  
**Fuente principal:** NASA Human Research Program — Integrated Medical Model (IMM)

## 1. Objetivo

Identificar y documentar las condiciones médicas relevantes para las misiones espaciales, sus posibles relaciones con los cinco peligros del vuelo espacial y los indicadores fisiológicos que podrían utilizarse para su monitoreo.

Este catálogo servirá como fundamento para seleccionar datasets, métricas y algoritmos del software.

## 2. Peligros espaciales

NASA identifica cinco peligros principales:

1. Radiación espacial.
2. Aislamiento y confinamiento.
3. Distancia de la Tierra.
4. Gravedad alterada.
5. Ambientes cerrados y hostiles.

Un mismo problema médico puede estar relacionado con más de un peligro, o presentarse independientemente de ellos.

## 3. Clasificación de condiciones médicas

### 3.1. Clasificación oficial del IMM

- Condiciones ambientales o inducidas por el vuelo espacial.
- Lesiones y traumatismos.
- Enfermedades y otras condiciones médicas.

### 3.2. Clasificación operativa propuesta

Para el desarrollo del software se investigarán:

- **Eventos médicos agudos:** condiciones de aparición rápida o reciente.
- **Urgencias médicas:** situaciones que requieren evaluación oportuna.
- **Emergencias médicas:** situaciones que pueden comprometer inmediatamente la vida o funciones vitales.

Estas categorías no son necesariamente excluyentes. Una condición aguda puede constituir una urgencia o emergencia dependiendo de su gravedad.

Esta clasificación es una propuesta del proyecto, no la clasificación oficial del IMM.

## 4. Matriz de trazabilidad biomédica

| ID | Condición médica | Categoría IMM | Peligro relacionado | Clasificación clínica propuesta | Parámetros de monitoreo | Fuente |
|---|---|---|---|---|---|---|
| MED-001 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |

Cada registro se completará a partir de documentación verificable.

| ID | Condición médica (NASA) | Grupo clínico NASA | Clasificación clínica propuesta | Parámetros candidatos | Estado |
|---|---|---|---|---|---|
| MED-001 | Sudden Cardiac Arrest | Cardiovascular Conditions | Emergencia | ECG, pulso, estado de conciencia | Investigación pendiente |
| MED-002 | Anaphylaxis | Allergic Reaction | Emergencia | Presión arterial, FC, SpO₂, síntomas respiratorios | Investigación pendiente |
| MED-003 | Atrial Fibrillation/Atrial Flutter | Cardiovascular Conditions | Urgencia o emergencia según gravedad | ECG, FC, presión arterial | Investigación pendiente |
| MED-004 | Acute Pancreatitis | Gastrointestinal Conditions | Urgencia o emergencia según gravedad | Dolor, temperatura, FC, presión arterial | Investigación pendiente |
| MED-005 | Headache (CO2-Induced) | Headache | Evento agudo; gravedad variable | Intensidad del dolor, CO₂ ambiental, síntomas neurológicos | Investigación pendiente |

**Notas:**
- Los nombres y grupos clínicos proceden de la documentación de NASA.
- La clasificación de urgencia es preliminar y propuesta por el equipo.
- Los parámetros son candidatos para investigar, no indicadores diagnósticos validados para el software.
- FC: frecuencia cardiaca; SpO₂: saturación periférica de oxígeno; ECG: electrocardiograma.

## 5. Ficha de investigación por condición

### MED-001 — Nombre de la condición

### MED-001 — Sudden Cardiac Arrest

**Nombre en español:** Paro cardiaco súbito.

**Categoría NASA IMM:** Cardiovascular Conditions.

**Clasificación clínica propuesta:** Emergencia médica.

**Estado:** Investigación preliminar.

#### Descripción médica

El paro cardiaco súbito consiste en la interrupción inesperada de la función mecánica efectiva del corazón, provocando la pérdida de circulación sanguínea adecuada.

Puede estar asociado con arritmias graves, entre otras causas.

No debe confundirse con un infarto de miocardio, aunque un infarto puede desencadenar un paro cardiaco.

#### Relación con los peligros espaciales

No se establece todavía una relación causal directa con alguno de los cinco peligros de NASA.

Se investigará si las alteraciones cardiovasculares asociadas con el vuelo espacial pueden modificar factores relevantes para esta condición.

La inclusión en el IMM no demuestra por sí misma que el vuelo espacial provoque paro cardiaco.

#### Clasificación clínica

**Emergencia médica.**

El paro cardiaco compromete inmediatamente la circulación y requiere intervención urgente.

Los signos principales de reconocimiento incluyen pérdida de respuesta y ausencia de respiración normal. El personal sanitario también puede evaluar rápidamente la presencia de pulso.

#### Parámetros fisiológicos y clínicos

| Parámetro | Utilidad |
|---|---|
| Electrocardiograma (ECG) | Identificar determinados ritmos y alteraciones de la actividad eléctrica cardiaca |
| Pulso | Evaluar la presencia de circulación pulsátil |
| Estado de conciencia | Reconocer pérdida de respuesta |
| Respiración | Identificar ausencia de respiración normal o respiración agónica |
| Presión arterial | Evaluación hemodinámica cuando es posible obtener una medición válida |
| SpO₂ | Información complementaria sobre oxigenación; no confirma ni descarta por sí sola un paro |

**Limitación fundamental:** La presencia de actividad eléctrica en el ECG no garantiza circulación sanguínea efectiva. El software no debe identificar automáticamente un paro cardiaco utilizando solamente la frecuencia cardiaca o el ECG.

#### Adquisición de datos

Posibles fuentes:

- Sistemas de adquisición de ECG.
- Sensores de pulso y fotopletismografía (PPG).
- Dispositivos de medición de presión arterial.
- Registro clínico de conciencia y respiración.

#### Datasets

Pendiente de identificar y evaluar.

Los datos deberán representar adecuadamente el fenómeno clínico que se desea investigar.

#### Métodos matemáticos candidatos

- Filtrado digital de ECG.
- Detección de complejos QRS.
- Análisis de intervalos RR.
- Identificación de determinados patrones arrítmicos.
- Evaluación de calidad de señal.
- Detección de cambios mediante algoritmos estadísticos.

Estos métodos son candidatos de investigación y no equivalen a un sistema validado de detección de paro cardiaco.

#### Limitaciones

1. Un algoritmo de arritmias no constituye automáticamente un detector de paro cardiaco.
2. El ECG no demuestra por sí solo circulación efectiva.
3. Las señales pueden presentar artefactos o interrupciones.
4. Los datasets terrestres pueden no representar adecuadamente las condiciones espaciales.
5. Cualquier alerta clínica requeriría validación específica.

#### Referencias

**NASA — Integrated Medical Model Documentation:**  
https://www.nasa.gov/integrated-medical-model-documentation/

**American Heart Association — Adult Basic Life Support Guidelines:**  
https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines/adult-basic-life-support/

**American Heart Association — What Is Cardiac Arrest?:**  
https://www.heart.org/en/health-topics/cardiac-arrest/about-cardiac-arrest

## 6. Criterios de documentación

- Diferenciar información oficial de NASA de hipótesis del equipo.
- Conservar la referencia de cada condición investigada.
- No confundir un indicador fisiológico con un diagnóstico.
- Registrar las limitaciones de los datasets.
- Evitar asumir relaciones causales sin evidencia.
- No asignar categorías de urgencia sin criterios clínicos que las respalden.

## 7. Fuentes de referencia

- [NASA — Integrated Medical Model](https://www.nasa.gov/nasa-integrated-medical-model-imm-overview/)
- [NASA — Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
- [NASA — Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)

### Catálogo oficial de condiciones médicas — IMM

**Institución:** NASA Engineering & Safety Center  
**Documento:** Trade Space Analyses: Balancing Crew and Mission Design Parameters  
**Año:** 2024  
**Identificador:** NASA/TM–20240011265  
**Ubicación:** Tabla 55, página 198 del informe  
**Contenido:** Lista de 100 condiciones médicas utilizadas en el Integrated Medical Model.

**Fuente primaria:**  
https://ntrs.nasa.gov/api/citations/20240011265/downloads/12-3-24%2020240011265.pdf

**Documentación clínica complementaria (CliFF):**  
https://www.nasa.gov/integrated-medical-model-documentation/

**Criterio de investigación:** Se conservarán los nombres originales de las condiciones médicas y se documentarán por separado sus indicadores fisiológicos, posibles niveles de urgencia y relaciones con los peligros espaciales.

## 8. Pendientes

- [ ] Localizar el listado oficial de condiciones del IMM.
- [ ] Registrar las condiciones con sus nombres originales.
- [ ] Verificar la categoría oficial de cada condición.
- [ ] Investigar las relaciones con los peligros espaciales.
- [ ] Identificar parámetros fisiológicos relevantes.
- [ ] Investigar datasets disponibles.
- [ ] Priorizar condiciones para implementar en el prototipo.
