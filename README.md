# NASA Astronaut Health Monitor

**NASA Space Apps Challenge 2026**

## 1. Descripción del proyecto

NASA Astronaut Health Monitor es un prototipo de software orientado al monitoreo de indicadores fisiológicos de astronautas durante misiones espaciales prolongadas.

El proyecto busca integrar conocimientos de medicina espacial, fisiología humana, procesamiento de señales y algoritmos matemáticos para facilitar la evaluación del estado de salud y la identificación de posibles alteraciones.

El software se desarrollará en Python y utilizará Streamlit como interfaz gráfica inicial.

## 2. Problemática

Durante los vuelos espaciales, los astronautas están expuestos a condiciones que pueden afectar su salud física, cognitiva y psicológica.

La distancia de la Tierra y las limitaciones de recursos también dificultan la atención médica durante misiones prolongadas.

NASA identifica cinco peligros principales:

| Peligro espacial | Riesgos asociados |
|---|---|
| Radiación espacial | Daño celular, efectos agudos de radiación y riesgos de salud a largo plazo |
| Aislamiento y confinamiento | Alteraciones del sueño, estrés y dificultades conductuales |
| Distancia de la Tierra | Limitaciones para recibir asistencia médica, suministros y evacuación |
| Gravedad alterada | Desacondicionamiento cardiovascular, atrofia muscular, pérdida ósea y alteraciones vestibulares |
| Ambientes cerrados y hostiles | Exposición a contaminantes, alteraciones ambientales y riesgos inmunológicos |

**Fuente:** [NASA — Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)

## 3. Condiciones médicas consideradas por NASA

NASA desarrolla el Integrated Medical Model (IMM), un sistema probabilístico utilizado para evaluar riesgos médicos y necesidades de recursos durante misiones espaciales.

El modelo base considera 100 condiciones médicas y existe una lista ampliada de 119 condiciones.

La clasificación oficial del IMM comprende:

1. Condiciones ambientales o inducidas por el vuelo espacial.
2. Lesiones y traumatismos.
3. Enfermedades y condiciones médicas.

**Fuente:** [NASA — Integrated Medical Model](https://www.nasa.gov/nasa-integrated-medical-model-imm-overview/)

## 4. Clasificación operativa propuesta para el software

Con fines de investigación, el proyecto propone estudiar las condiciones médicas desde tres perspectivas de atención.

Esta clasificación es preliminar y no debe interpretarse como una escala oficial de triaje de NASA.

### 4.1. Eventos médicos agudos

Condiciones de aparición reciente o rápida que producen cambios en el estado del astronauta.

Ejemplo: cinetosis espacial.

Parámetros de interés:

- Frecuencia cardiaca.
- Episodios de vómito.
- Intensidad y duración de síntomas.
- Capacidad para realizar actividades.

### 4.2. Urgencias médicas

Condiciones que requieren una evaluación médica oportuna, aunque no necesariamente representan un peligro vital inmediato.

Ejemplo: cólico renal asociado con cálculos renales sin complicaciones graves.

Parámetros de interés:

- Intensidad del dolor.
- Temperatura corporal.
- Frecuencia cardiaca.
- Características urinarias.

### 4.3. Emergencias médicas

Condiciones que pueden comprometer inmediatamente la vida o funciones vitales y requieren intervención inmediata.

Ejemplos: paro cardiaco súbito y anafilaxia grave.

Parámetros de interés:

- Actividad eléctrica cardiaca (ECG).
- Frecuencia cardiaca.
- Presión arterial.
- Saturación de oxígeno.
- Frecuencia respiratoria.
- Estado de conciencia y síntomas clínicos.

**Nota:** Las condiciones, categorías e indicadores requieren evaluación científica y clínica. Una medición aislada no permite confirmar una enfermedad ni determinar automáticamente su gravedad.

## 5. Modelo científico del proyecto

El desarrollo seguirá la siguiente secuencia:

**Peligros espaciales → Riesgos para la salud → Condiciones médicas → Indicadores clínicos y fisiológicos → Datasets → Procesamiento matemático → Monitoreo y evaluación.**

Las relaciones no necesariamente son uno a uno. Una condición puede relacionarse con varios peligros, y algunas enfermedades pueden ocurrir independientemente del ambiente espacial.

## 6. Metodología de investigación

### Fase 1. Investigación de riesgos

Identificar los riesgos asociados con cada uno de los cinco peligros espaciales.

### Fase 2. Investigación de condiciones médicas

Consultar las condiciones documentadas por NASA y organizar un catálogo con sus características y posibles grados de gravedad.

### Fase 3. Selección de indicadores

Relacionar cada condición con los parámetros fisiológicos, clínicos y ambientales que puedan aportar información relevante.

### Fase 4. Búsqueda de datasets

Identificar conjuntos de datos científicos adecuados y documentar su procedencia, variables, calidad y limitaciones.

### Fase 5. Desarrollo matemático

Seleccionar e implementar métodos de procesamiento de señales, análisis estadístico y detección de anomalías.

### Fase 6. Desarrollo del software

Integrar los algoritmos con una interfaz gráfica que permita visualizar indicadores, tendencias y posibles alertas.

### Fase 7. Evaluación

Comprobar el comportamiento de los algoritmos mediante pruebas reproducibles, datos de referencia y métricas de desempeño.

## 7. Tecnologías

| Tecnología | Función |
|---|---|
| Python 3.12.15 | Lenguaje de programación |
| Streamlit | Interfaz gráfica |
| NumPy y SciPy | Cálculo científico y procesamiento de señales |
| Pandas | Administración de datos |
| Matplotlib | Visualización científica |
| scikit-learn | Métodos estadísticos y aprendizaje automático |
| pytest | Pruebas automatizadas |
| Git y GitHub | Control de versiones y colaboración |

## 8. Documentación

- [Arquitectura del software](docs/architecture.md)
- [Estado de desarrollo](docs/development_status.md)
- [Fundamentación científica](docs/scientific_foundation.md)
- [Catálogo de condiciones médicas](docs/medical_conditions_catalog.md)

## 8.1. Demostración integrada

Inicia la aplicación desde la raíz del repositorio:

```bash
python -m streamlit run app.py
```

Después de autenticarte, selecciona un escenario y una modalidad:

- **Simulación categórica:** usa las categorías ECG sintéticas del simulador para demostrar reglas y transiciones; no ejecuta detección matemática ECG.
- **Análisis ECG experimental:** genera muestras ECG sintéticas, procesa esas mismas muestras con `ecg_processing.py`, `qrs_detection.py` y `vf_detection.py`, y entrega sus categorías al monitor.

`Iniciar simulación` procesa la primera muestra. `Avanzar muestra` procesa una muestra adicional y `Ejecutar restante` completa la secuencia. El historial y el estado se conservan en la sesión de Streamlit. El escenario es una referencia de demostración; el estado mostrado procede del pipeline, las reglas y la máquina de estados.

Para ejecutar las pruebas:

```bash
pytest
```

La aplicación es `simulation_only`: no constituye un dispositivo médico validado, no diagnostica FV ni paro cardiaco y no proporciona recomendaciones de tratamiento.

## 9. Alcance

El sistema es un prototipo experimental desarrollado durante NASA Space Apps Challenge 2026.

No constituye un dispositivo médico validado ni reemplaza el juicio clínico, los protocolos médicos de vuelo o la atención de profesionales sanitarios.

## 10. Referencias principales

1. [NASA — Health Monitoring Software Challenge](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/)
2. [NASA — Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)
3. [NASA — Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
4. [NASA — Integrated Medical Model](https://www.nasa.gov/nasa-integrated-medical-model-imm-overview/)
5. [NASA — Integrated Medical Model Documentation](https://www.nasa.gov/integrated-medical-model-documentation/)
