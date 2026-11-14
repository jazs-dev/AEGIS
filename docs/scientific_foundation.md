# Fundamentación científica y biomédica

**Proyecto:** NASA Astronaut Health Monitor  
**Evento:** NASA Space Apps Challenge 2026  
**Estado:** Fundamentación científica preliminar  
**Área:** Medicina espacial, ingeniería biomédica y procesamiento de señales fisiológicas.

---

## 1. Planteamiento del problema

Las misiones espaciales exponen a los astronautas a condiciones ambientales, fisiológicas y operativas diferentes de las experimentadas en la Tierra.

Estas condiciones pueden producir alteraciones en distintos sistemas del organismo, incrementar determinados riesgos médicos y dificultar la atención sanitaria durante misiones prolongadas.

NASA, mediante su Human Research Program (HRP), identifica cinco peligros principales asociados con los vuelos espaciales.

El presente proyecto propone estudiar las relaciones entre estos peligros, los riesgos para la salud humana, las condiciones médicas y los parámetros fisiológicos que podrían permitir su monitoreo.

La finalidad es fundamentar científicamente la selección de variables y los métodos matemáticos que posteriormente se implementarán en el software.

## 2. Los cinco peligros espaciales identificados por NASA

| ID | Peligro espacial | Descripción |
|---|---|---|
| H-01 | Space Radiation | Exposición a radiación espacial |
| H-02 | Isolation and Confinement | Aislamiento social y confinamiento prolongado |
| H-03 | Distance from Earth | Distancia de la Tierra y limitaciones de asistencia y comunicación |
| H-04 | Altered Gravity Fields | Exposición a microgravedad y otros campos gravitacionales |
| H-05 | Hostile/Closed Environments | Condiciones ambientales de espacios habitables cerrados y potencialmente hostiles |

**Fuente:** [NASA — Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)

Estos peligros pueden interactuar entre sí y producir efectos combinados.

No todos causan directamente enfermedades. Por ejemplo, la distancia de la Tierra es principalmente un factor operativo que condiciona la posibilidad de recibir asistencia médica.

## 3. Del peligro espacial al riesgo para la salud

Un peligro espacial puede contribuir a diferentes riesgos para la salud, pero un riesgo no equivale necesariamente a una enfermedad diagnosticada.

Se utilizarán las siguientes definiciones:

- **Peligro:** condición ambiental u operativa capaz de afectar la salud.
- **Riesgo:** posibilidad de sufrir un efecto adverso, considerando su probabilidad y consecuencias.
- **Alteración fisiopatológica:** cambio en el funcionamiento normal del organismo asociado con un proceso patológico.
- **Condición médica:** enfermedad, lesión o situación clínica identificable.
- **Indicador fisiológico:** variable medible que aporta información sobre una función del organismo.

### 3.1. Relaciones iniciales

| Peligro | Riesgos o efectos relacionados | Ejemplos de condiciones o alteraciones |
|---|---|---|
| H-01: Radiación espacial | Daño celular y efectos de radiación | Síndrome agudo por radiación bajo exposiciones suficientemente elevadas; riesgos oncológicos a largo plazo |
| H-02: Aislamiento y confinamiento | Alteraciones del sueño, estado psicológico y rendimiento | Trastornos del sueño y dificultades de adaptación conductual |
| H-03: Distancia de la Tierra | Limitación de asistencia médica y evacuación | Agravamiento de consecuencias ante emergencias no tratadas oportunamente |
| H-04: Gravedad alterada | Desacondicionamiento cardiovascular, cambios vestibulares y pérdida ósea | Cinetosis espacial, intolerancia ortostática, alteraciones musculoesqueléticas |
| H-05: Ambientes cerrados y hostiles | Exposición a contaminantes, CO₂ elevado, hipoxia y alteraciones ambientales | Cefalea asociada con CO₂, intoxicaciones y lesiones relacionadas con cambios de presión |

**Fuentes:** NASA Human Research Program y documentación del Integrated Medical Model.

Las relaciones presentadas son ejemplos iniciales. Cada relación específica deberá verificarse antes de incorporarse como fundamento de un algoritmo.

## 4. Clasificación de condiciones médicas

Para evitar confusiones, se utilizarán dos sistemas complementarios.

### 4.1. Clasificación oficial del Integrated Medical Model (IMM)

NASA utiliza el IMM para modelar condiciones médicas y necesidades de recursos durante misiones espaciales.

Su modelo base considera 100 condiciones médicas, mientras que su documentación ampliada contempla 119 condiciones.

Las tres categorías generales del IMM son:

1. **Environmental Conditions:** condiciones ambientales o inducidas por el entorno espacial.
2. **Injury/Trauma:** lesiones y traumatismos.
3. **Illness/Other Medical Conditions:** enfermedades y otras condiciones médicas.

Esta clasificación se conservará al registrar cada condición.

### 4.2. Clasificación clínica operativa del proyecto

Adicionalmente, el equipo propone analizar dos dimensiones clínicas independientes.

**Dimensión A: Inicio y evolución**

- **Evento médico agudo:** condición que aparece de forma rápida o reciente.
- **Condición subaguda o crónica:** condición que evoluciona durante periodos más prolongados.

**Dimensión B: Necesidad de atención**

- **Urgencia médica:** situación que requiere evaluación y atención oportuna.
- **Emergencia médica:** situación que amenaza inmediatamente la vida o funciones vitales y necesita intervención inmediata.
- **Condición no urgente:** situación que puede manejarse mediante seguimiento o evaluación programada, según su presentación clínica.

Una condición aguda puede ser no urgente, urgente o emergente.

Estas clasificaciones son preliminares y deberán fundamentarse en criterios clínicos. No sustituyen los protocolos de atención médica de NASA.

## 5. Ejemplos de condiciones médicas

Las siguientes condiciones se encuentran contempladas en la documentación médica de NASA. Su clasificación por gravedad es una propuesta ilustrativa del equipo.

| Condición médica | Presentación clínica | Posible nivel de atención | Indicadores candidatos |
|---|---|---|---|
| Space Motion Sickness | Aguda | Variable, usualmente no emergente | Náuseas, vómitos, frecuencia cardiaca, tolerancia a actividades |
| Headache (CO₂-Induced) | Aguda o recurrente | Variable según síntomas y exposición | Cefalea, concentración ambiental de CO₂, síntomas neurológicos |
| Renal Stones | Aguda si produce cólico renal | Urgencia; emergencia si presenta complicaciones graves | Dolor, temperatura, frecuencia cardiaca, indicadores urinarios |
| Sudden Cardiac Arrest | Aguda | Emergencia | ECG, pulso, respiración y estado de conciencia |
| Anaphylaxis | Aguda | Emergencia | Presión arterial, frecuencia cardiaca, SpO₂ y signos respiratorios |

**Nota:** Las variables propuestas no necesariamente permiten detectar por sí mismas la condición médica. Algunas requieren evaluaciones clínicas, pruebas complementarias o sensores específicos.

## 6. Selección de parámetros fisiológicos

El software no seleccionará variables únicamente porque estén disponibles en un sensor.

La selección deberá partir de una condición médica o un riesgo fisiológico previamente justificado.

### 6.1. Parámetros candidatos

| Sistema o dominio | Parámetros | Posible aplicación |
|---|---|---|
| Cardiovascular | Frecuencia cardiaca, ECG, variabilidad de frecuencia cardiaca, presión arterial | Evaluación del funcionamiento cardiovascular |
| Respiratorio | Frecuencia respiratoria, SpO₂ | Seguimiento respiratorio y de oxigenación |
| Neurológico y cognitivo | Tiempo de reacción, pruebas cognitivas, EEG cuando esté justificado | Evaluación de funciones neurológicas específicas |
| Termorregulación | Temperatura corporal | Seguimiento de alteraciones térmicas |
| Musculoesquelético | Fuerza muscular, movilidad y desempeño funcional | Evaluación del desacondicionamiento |
| Sueño y actividad | Duración del sueño, actividad física, patrones circadianos | Evaluación de descanso y rendimiento |
| Renal y metabólico | Diuresis, análisis urinarios y otros indicadores clínicos | Evaluación renal y metabólica |
| Ambiental | CO₂, O₂, presión ambiental y dosis de radiación | Evaluación de exposición y condiciones del entorno |

Las mediciones ambientales no son parámetros fisiológicos, pero pueden ayudar a interpretar los cambios observados en el organismo.

La disponibilidad de sensores y la posibilidad de adquirir cada indicador durante una misión deberán investigarse por separado.

## 7. Modelo de trazabilidad científica

El proyecto seguirá el siguiente esquema:

**Peligro espacial → Riesgo para la salud → Alteración fisiopatológica o condición médica → Caracterización clínica → Parámetros fisiológicos y ambientales → Datos → Métricas y algoritmos → Resultados de monitoreo.**

Este modelo no presupone una relación causal directa entre todos los elementos.

Cada enlace deberá documentarse utilizando evidencia científica.

### 7.1. Ejemplo: gravedad alterada y adaptación cardiovascular

| Etapa | Elemento |
|---|---|
| Peligro | Altered Gravity Fields |
| Riesgo | Desacondicionamiento cardiovascular |
| Alteración | Cambios en la regulación cardiovascular y tolerancia ortostática |
| Condición relacionada | Intolerancia ortostática |
| Parámetros | Frecuencia cardiaca y presión arterial durante evaluaciones apropiadas |
| Datos | Registros cardiovasculares con contexto y condiciones de medición |
| Métodos candidatos | Análisis temporal, cambios respecto a la línea basal y tendencias |
| Objetivo | Identificar variaciones que ameriten evaluación adicional |

Los parámetros y algoritmos son propuestas iniciales. No constituyen un procedimiento diagnóstico validado.

## 8. Metodología de investigación

### Fase 1. Identificación de peligros

Registrar los cinco peligros espaciales y sus mecanismos de exposición.

### Fase 2. Investigación de riesgos

Consultar los riesgos para la salud humana documentados por NASA y determinar su relación con cada peligro.

### Fase 3. Identificación de condiciones médicas

Utilizar el catálogo IMM y otras fuentes clínicas para registrar enfermedades, lesiones y alteraciones relevantes.

### Fase 4. Caracterización clínica

Documentar el tipo de presentación, gravedad posible, evolución y necesidad de atención, con respaldo bibliográfico.

### Fase 5. Selección de indicadores

Identificar las variables que ofrecen información sobre cada condición y determinar sus limitaciones clínicas.

### Fase 6. Investigación de datasets

Buscar conjuntos de datos y evaluar:

- Procedencia y población.
- Variables y unidades.
- Frecuencia de muestreo.
- Calidad y datos faltantes.
- Etiquetas clínicas y criterios diagnósticos.
- Representatividad de las condiciones espaciales.
- Licencia y condiciones de uso.

### Fase 7. Selección de algoritmos

Investigar métodos matemáticos adecuados para los datos disponibles.

Se considerarán técnicas de filtrado, extracción de características, análisis estadístico y detección de anomalías.

### Fase 8. Implementación y evaluación

Implementar los algoritmos y evaluar su funcionamiento, reproducibilidad, desempeño computacional y limitaciones.

Posteriormente se integrarán en el software de monitoreo.

## 9. Criterios científicos del proyecto

1. No confundir peligros, riesgos, alteraciones fisiológicas y enfermedades.
2. No considerar que todas las condiciones médicas son causadas por el vuelo espacial.
3. No interpretar un parámetro fisiológico aislado como diagnóstico.
4. No asumir que los datasets terrestres representan completamente a la población de astronautas.
5. Diferenciar relaciones documentadas por NASA de hipótesis del equipo.
6. Mantener trazabilidad entre cada condición, su evidencia científica y el algoritmo implementado.
7. Reconocer explícitamente las limitaciones del prototipo.

## 10. Documentación complementaria

La investigación detallada de cada condición se registrará en:

[Catálogo de condiciones médicas](medical_conditions_catalog.md)

Las decisiones tecnológicas y de arquitectura estarán documentadas en:

[Arquitectura del software](architecture.md)

## 11. Referencias

1. NASA Human Research Program. [Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/).
2. NASA Human Research Program. [Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/).
3. NASA. [Integrated Medical Model Overview](https://www.nasa.gov/nasa-integrated-medical-model-imm-overview/).
4. NASA. [Integrated Medical Model Documentation](https://www.nasa.gov/integrated-medical-model-documentation/).
5. NASA. [Human System Risk Board](https://www.nasa.gov/directorates/esdmd/hhp/human-system-risk-board/).

## 12. Estado de investigación

- [x] Identificación de los cinco peligros espaciales.
- [x] Definición del modelo conceptual de trazabilidad.
- [x] Identificación de fuentes oficiales de NASA.
- [ ] Investigación exhaustiva de riesgos fisiológicos.
- [ ] Registro del catálogo completo de condiciones médicas.
- [ ] Caracterización clínica de cada condición seleccionada.
- [ ] Selección de parámetros fisiológicos prioritarios.
- [ ] Investigación de datasets.
- [ ] Selección y fundamentación de algoritmos.
- [ ] Validación experimental del prototipo.