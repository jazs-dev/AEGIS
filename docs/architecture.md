# Arquitectura del software

## Proyecto
NASA Astronaut Health Monitor

Software de monitoreo de indicadores fisiológicos para astronautas, desarrollado como prototipo para NASA Space Apps Challenge 2026.

## Decisión técnica 001: Uso de Streamlit

**Estado:** Adoptada para el prototipo.

### Tecnología seleccionada
- Lenguaje principal: Python 3.12.15
- Framework de interfaz: Streamlit
- Entorno de desarrollo: Visual Studio Code
- Control de versiones: Git y GitHub

### Justificación

Se seleccionó Streamlit para desarrollar una interfaz gráfica interactiva utilizando Python, sin necesidad de implementar inicialmente un frontend independiente con HTML, CSS y JavaScript.

Esto permitirá concentrar el trabajo del equipo en el procesamiento de señales fisiológicas, la implementación de algoritmos matemáticos y la visualización de resultados.

### Función de Streamlit

Streamlit será responsable de:

1. Mostrar indicadores fisiológicos.
2. Visualizar señales y tendencias mediante gráficas.
3. Presentar los resultados de los algoritmos.
4. Mostrar alertas y explicaciones de posibles anomalías.
5. Permitir la interacción del usuario con el prototipo.

### Arquitectura propuesta

- `app.py`: punto de entrada de la aplicación.
- `src/processing/`: procesamiento de señales fisiológicas.
- `src/algorithms/`: algoritmos matemáticos y estadísticos.
- `src/monitoring/`: evaluación de indicadores y generación de alertas.
- `data/`: conjuntos de datos de prueba.
- `tests/`: pruebas automatizadas.
- `docs/`: documentación técnica.

### Consideraciones

- La aplicación se ejecutará localmente durante el desarrollo.
- Los algoritmos de análisis deberán funcionar independientemente de Streamlit.
- Se priorizarán métodos interpretables y computacionalmente eficientes.
- Las alertas del prototipo no constituyen diagnósticos médicos.
- La arquitectura podrá modificarse conforme se definan los requisitos del proyecto.

### Alternativas

Una aplicación de escritorio nativa o una interfaz web con frontend independiente podrían ofrecer ventajas en otros escenarios. Se prioriza Streamlit por su simplicidad de implementación para el hackathon.