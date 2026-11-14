# Reglas de organización

- Organizar el código por responsabilidad en carpetas dentro de `src/`.
- Mantener `app.py` como punto de entrada mínimo, sin lógica de negocio.
- Colocar autenticación en `src/auth/`, interfaz en `src/ui/` y pantallas en `src/ui/views/`.
- Guardar estilos e imágenes en `assets/`, configuración de Streamlit en `.streamlit/`, documentación en `docs/` y pruebas en `tests/`.
- Mantener procesamiento, algoritmos y monitoreo independientes de la interfaz.
- Crear subcarpetas cuando agrupen una responsabilidad real; evitar carpetas vacías sin propósito.
- Nunca guardar credenciales reales en el repositorio.
