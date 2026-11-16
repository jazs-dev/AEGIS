# Protocolo de validación experimental del detector FV

## Objetivo

Medir el baseline congelado del detector determinista actual sobre segmentos ECG reales con anotaciones de ritmo. Esta etapa no modifica filtros, ventanas, parámetros QRS ni umbrales FV.

La hipótesis operacional es que una ventana anotada como FV tendrá mayor probabilidad de recibir `vf_compatible` que una ventana anotada con otro ritmo. El resultado es una evaluación técnica del algoritmo, no validación clínica ni autorización de tratamiento.

## Baseline congelado

La configuración es `config/ecg_algorithm_parameters.json`, versión `0.1.0`, SHA-256:

```text
2e8ce27f1eddd97eb8b9205da67629cec35f8bc9cc7b3d5b383284365a4224d3
```

Incluye ventana de 4 s, análisis amplio `0.5–30 Hz`, ruta QRS `5–15 Hz`, características RMS/energía/espectro/entropía/TCI y umbrales experimentales. Se ejecuta `process_ecg()`, luego `detect_qrs()` y finalmente `classify_ecg()` sin recibir etiquetas de referencia.

## Datasets

Se admiten dos especificaciones versionadas:

- **CUDB 1.0.0:** 35 registros ECG de aproximadamente ocho minutos, digitalizados a 250 Hz, 12 bits y rango de 10 V. Incluye VT, flutter ventricular y FV. PhysioNet advierte que los archivos de anotación son auxiliares, que los límites de inicio de FV son aproximados y que la base se define como taquiarritmia, no exclusivamente fibrilación. Fuente: <https://physionet.org/content/cudb/1.0.0/>.
- **VFDB 1.0.0:** 22 registros de media hora. Los `.atr` contienen cambios de ritmo, no etiquetas por latido. `VF` y `VFIB` significan fibrilación ventricular; `VT` y `VFL` se conservan como ritmos distintos y son negativos para el endpoint binario. `AFIB`, `ASYS`, `NOISE`, `NSR` y otras etiquetas se preservan en `reference_rhythm`. Fuente: <https://physionet.org/content/vfdb/1.0.0/>.

Ambas bases tienen licencia ODC-By 1.0 según sus páginas oficiales. Los registros originales no se guardan en Git.

## Cargador y anotaciones

`src/datasets/physionet_loader.py` usa `wfdb` y acepta:

```bash
python scripts/evaluate_vf.py vfdb 418 --output data/processed/vf_evaluation
python scripts/evaluate_vf.py cudb cu01 --local-root data/raw/physionet
```

El cargador funciona con `pn_dir` remoto cuando existe conectividad o con una raíz local que contiene `.hea`, `.dat` y `.atr`. Conserva frecuencia, canal, unidades, identificador, versión y fuente. El entorno reproducible fija `wfdb==4.2.0` y `pandas==2.3.3`.

`src/datasets/rhythm_annotations.py` transforma anotaciones de cambios de ritmo a intervalos, sin pasar el texto clínico al detector. El mapeo binario es:

| Etiqueta | `reference_label` | `reference_rhythm` |
|---|---|---|
| `VF`, `VFIB` | `VF` | se conserva |
| `VT`, `VFL`, `AFIB`, `NSR`, `ASYS` y otras conocidas | `NON_VF` | se conserva |
| `NOISE` | `EXCLUDED` | `NOISE` |
| desconocida | `AMBIGUOUS` | texto original |

AFIB nunca se transforma en FV; VT y VFL no se agrupan clínicamente con FV.

## Segmentación y política de referencia

La evaluación inicial usa ventanas completas no solapadas de 4 s. Una ventana completamente contenida en un intervalo VF es positiva; una ventana completamente contenida en un ritmo conocido no VF es negativa. Toda ventana que cruce un cambio de anotación es `AMBIGUOUS` y se conserva en el CSV, pero se excluye de la métrica binaria principal. Las ventanas sin cobertura válida son `EXCLUDED`.

El final de una ventana representa el momento en que el detector dispone de ella. No se atribuye la detección al inicio de la ventana.

## Predicciones y abstenciones

- `vf_compatible` → predicción `VF`.
- `normal_sinus`, `abnormal_non_vf` → predicción `NON_VF`.
- `uninterpretable`, `not_assessed` o calidad no válida → `ABSTAIN`.

El informe presenta métricas sobre ventanas binarias interpretables, cobertura y un análisis adicional en que una abstención dentro de una ventana VF se contabiliza como FN. No se eliminan silenciosamente segmentos difíciles.

Para la latencia, `first_detection_available_seconds` usa el final de la ventana que produjo la primera predicción `VF`. El retardo se calcula contra el inicio anotado del episodio y se marca como aproximado para CUDB. También se registran predicciones VF fuera de episodios anotados como falsas alarmas.

## Métricas

Se calculan TP, FP, TN, FN, sensibilidad, especificidad, precisión, F1 y exactitud. Un denominador cero devuelve `null`, no un valor inventado. También se generan agrupaciones por dataset, registro, tipo de ritmo y calidad ECG. Los conteos de ventanas no se interpretan como conteos de pacientes independientes.

El evaluador guarda `evaluation_report.json`, `segment_results.csv` y figuras PNG en `data/processed/vf_evaluation/`. Cada ejecución registra dataset, registros, canal, ventana, solapamiento, versión/hash de parámetros y exclusiones. La fecha de ejecución se registra para trazabilidad; las señales originales no se copian al resultado.

## Estado de esta ejecución

La resolución DNS directa falló, pero el endpoint S3 público oficial de PhysioNet respondió. Se descargaron y verificaron por SHA-256 seis registros: VFDB `422`, `424`, `426`, `430` y CUDB `cu01`, `cu03`. La evaluación real combinada produjo 2,030 ventanas binarias, 90 abstenciones y reportes en `data/processed/vf_evaluation/combined_baseline_20261115_with_examples/`. El detalle numérico está en [vf_baseline_results.md](vf_baseline_results.md).

La evaluación es un subconjunto preliminar; no representa la colección completa ni una validación clínica.

## Limitaciones

CUDB informa inicios de FV aproximados y episodios precedidos por VT, por lo que un detector puede alertar antes del límite anotado. VFDB ofrece cambios de ritmo y no etiquetas de latidos. Las ventanas dentro de un mismo registro no son observaciones independientes. El detector actual es experimental y sus parámetros no están clínicamente validados. Antes de optimizar, debe congelarse una partición de desarrollo y reservar registros independientes para evaluación final.
