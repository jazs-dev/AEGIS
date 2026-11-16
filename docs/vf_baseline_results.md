# Resultados baseline del detector experimental de FV

## Objetivo

Evaluar sin optimización la configuración congelada del detector determinista sobre registros ECG reales de PhysioNet. Estos resultados son técnicos y preliminares; no constituyen validación clínica.

## Configuración y datos

- Detector: `config/ecg_algorithm_parameters.json`, versión `0.1.0`.
- SHA-256 de parámetros: `2e8ce27f1eddd97eb8b9205da67629cec35f8bc9cc7b3d5b383284365a4224d3`.
- Ventanas: 4 s, sin solapamiento.
- Disponibilidad temporal: final de la ventana completa.
- Canal: canal 0, `ECG`, unidad `mV`.
- Datasets: CUDB 1.0.0 y VFDB 1.0.0.
- Registros: VFDB `422`, `424`, `426`, `430`; CUDB `cu01`, `cu03`.
- Archivos originales y checksums: `data/raw/physionet/`; no están versionados en Git.

La selección se hizo inspeccionando `.atr`: todos los registros contienen anotaciones `VF` o `VFIB`. VT, VFL, AFIB, ruido y otros ritmos se mantuvieron diferenciados según el protocolo. CUDB se interpretó con un intervalo inicial no-VF antes del marcador aproximado de FV, conforme a su documentación oficial.

## Resultados globales

Informe reproducible: `data/processed/vf_evaluation/combined_baseline_20261115_with_examples/evaluation_report.json`.

Se obtuvieron 2,030 ventanas con etiqueta binaria: 650 FV y 1,380 no-FV. Hubo 90 abstenciones; 1,940 ventanas fueron interpretables para la matriz principal.

| Métrica | Resultado |
|---|---:|
| TP | 445 |
| FP | 290 |
| TN | 1,008 |
| FN | 197 |
| Sensibilidad | 0.6931 |
| Especificidad | 0.7766 |
| Precisión | 0.6054 |
| F1 | 0.6463 |
| Exactitud | 0.7490 |
| Cobertura interpretable | 95.57% |
| Abstenciones | 90 |

Si las abstenciones en ventanas FV se contabilizan adicionalmente como FN, la sensibilidad es 0.6846, la precisión 0.6054 y el F1 0.6426. Esta es una lectura de seguridad adicional, no una segunda ejecución del detector.

## Resultados por registro

| Registro | TP | FP | TN | FN | Sensibilidad | Especificidad | Abstenciones |
|---|---:|---:|---:|---:|---:|---:|---:|
| CUDB/cu01 | 52 | 0 | 53 | 21 | 0.7123 | 1.0000 | 0 |
| CUDB/cu03 | 6 | 3 | 110 | 2 | 0.7500 | 0.9735 | 5 |
| VFDB/422 | 106 | 64 | 261 | 20 | 0.8413 | 0.8031 | 6 |
| VFDB/424 | 23 | 149 | 203 | 3 | 0.8846 | 0.5767 | 67 |
| VFDB/426 | 127 | 10 | 223 | 30 | 0.8089 | 0.9571 | 2 |
| VFDB/430 | 131 | 64 | 158 | 121 | 0.5198 | 0.7117 | 10 |

Las ventanas no son pacientes independientes; por ello no se presentan estos conteos como validación poblacional.

## Errores por ritmo de referencia

Los falsos positivos binarios se concentraron principalmente en:

- Ritmo normal `N`: 158 FP.
- Taquicardia ventricular `VT`: 80 FP.
- Flutter ventricular `VFL`: 21 FP.
- Actividad ectópica ventricular de alto grado `HGEA`: 10 FP.
- Ritmo sinusal normal `NSR`: 8 FP.
- Bloqueo/bigeminia `BI`: 5 FP.
- Asistolia `ASYS`: 5 FP.
- Bradicardia sinusal `SBR`: 1 FP.

Las ventanas `NOISE`, transiciones ambiguas y etiquetas sin cobertura binaria no se mezclaron con FP/TN. Las categorías VF positivas fueron `VF` (316 TP, 174 FN) y `VFIB` (129 TP, 23 FN).

Estos conteos describen asociaciones observadas. No demuestran que una característica aislada haya causado el error. El patrón es compatible con una baja especificidad frente a ritmos organizados/ventriculares en algunos registros, pero requiere revisión de las formas de onda y de las anotaciones.

## Tiempo de detección

Se identificaron 15 episodios/intervalos positivos derivados de las anotaciones seleccionadas; todos tuvieron al menos una ventana con predicción FV. Los retardos aproximados disponibles fueron:

```text
4 s: 11 episodios
8 s: 1 episodio
16 s: 1 episodio
20 s: 1 episodio
32 s: 1 episodio
```

La lista detallada está en el campo `temporal` del JSON. Los límites de CUDB son aproximados y el tiempo corresponde al final de la primera ventana detectada, no al inicio de esa ventana.

## Ejemplos y trazabilidad

Cada ejecución con registros cargados genera:

- `confusion_matrix.png`
- `prediction_distribution.png`
- `feature_distributions.png`
- `examples/tp_*.png`
- `examples/fp_*.png`
- `examples/fn_*.png`
- `examples/tn_*.png`
- `examples/abstain_*.png`
- `segment_results.csv` con intervalo, etiqueta, predicción y características.

Los ejemplos actuales se encuentran en `data/processed/vf_evaluation/combined_baseline_20261115_with_examples/examples/`. Las señales graficadas son las ventanas reales cargadas desde WFDB; no son señales sintéticas.

## Limitaciones y conclusión

La evaluación usa seis registros, una ventana no solapada y un único canal. Existe dependencia entre ventanas del mismo registro y no se calcularon intervalos de confianza por paciente. CUDB advierte que los inicios de FV son aproximados y VFDB utiliza anotaciones de cambios de ritmo, no de latido. El detector no fue optimizado ni modificado.

El baseline detectó aproximadamente 69.31% de las ventanas FV interpretables y produjo 290 falsos positivos sobre 1,380 ventanas no-FV. La especificidad global fue 77.66%. Estos resultados son preliminares, específicos de los registros y parámetros indicados, y no deben interpretarse como rendimiento clínico.
