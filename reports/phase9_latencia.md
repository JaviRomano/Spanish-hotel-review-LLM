# Fase 9 · Latencia por etapa (uso interactivo)

Generado por `uv run just latencia` a partir de `results/latencia_v6_A_20261029-2234.jsonl`. No editar a mano.

- Fecha: 2026-10-29T22:34:23 · Ollama 0.40.8
- Generador `qwen3.6:27b-q4_K_M` (prompt v6) · juez `gemma4:12b-it-qat` (rúbrica v2g) · embeddings `bge-m3` · clasificador mRoBERTa (3 semillas, CPU)
- Muestra: `evals/latencia/muestra_v1.json`, 6 reseñas × 3 repeticiones = 18 medidas. Cada repetición descarga todos los modelos, precarga juez y generador (como la app) y procesa las reseñas una a una.
- Sin caché de resultados: 0 llamadas al LLM salieron de la caché (correcto: todas se midieron).

Cifras: **mediana / p90 en segundos**. Con tan pocas medidas el p90 es casi el máximo.

## ¿Cuánto es carga y cuánto inferencia?

Carga = `load_duration` de las llamadas a Ollama más el tiempo de pared de la precarga de `require_gpu` (un generate con el prompt vacío que carga el modelo pero devuelve las métricas a cero). Inferencia = `prompt_eval_duration` + `eval_duration`. Resto = clasificador en CPU, normalización, comprobaciones y comunicación con Ollama.

| Reseñas | n | Total | Carga | Inferencia | Resto | % carga (suma) |
|---|---|---|---|---|---|---|
| Primera de cada repetición | 3 | 25.3 / 25.4 | 11.3 / 11.3 | 13.5 / 13.5 | 0.5 / 0.6 | 45% |
| Resto | 15 | 48.2 / 52.2 | 33.2 / 33.6 | 15.0 / 18.6 | 0.5 / 0.7 | 66% |
| Resto · destino publicable | 6 | 48.0 / 51.1 | 33.4 / 33.5 | 15.6 / 17.2 | 0.6 / 0.6 | 67% |
| Resto · destino revisión humana | 9 | 48.6 / 52.5 | 33.2 / 33.6 | 15.0 / 18.6 | 0.5 / 0.7 | 66% |

## Tiempo de pared por etapa

| Etapa | Primera reseña | Resto | Carga en la etapa (resto) | Modelos en VRAM al acabar |
|---|---|---|---|---|
| normalizacion | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | gemma4:12b-it-qat (ctx 8192) |
| clasificador | 0.1 / 0.1 | 0.1 / 0.3 | 0.0 / 0.0 | gemma4:12b-it-qat (ctx 8192) |
| embeddings | 2.5 / 2.5 | 2.4 / 2.5 | 2.3 / 2.3 | gemma4:12b-it-qat (ctx 8192) |
| carga_generador | 0.0 / 0.0 | 22.0 / 22.3 | 22.0 / 22.3 | qwen3.6:27b-q4_K_M (ctx 8192) |
| analisis | 4.3 / 4.3 | 6.1 / 10.0 | 0.0 / 0.0 | qwen3.6:27b-q4_K_M (ctx 8192) |
| respuesta | 5.7 / 5.7 | 5.1 / 5.6 | 0.0 / 0.0 | qwen3.6:27b-q4_K_M (ctx 8192) |
| checks | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | qwen3.6:27b-q4_K_M (ctx 8192) |
| carga_juez | 9.0 / 9.0 | 9.0 / 9.0 | 9.0 / 9.0 | gemma4:12b-it-qat (ctx 8192) |
| juez | 3.6 / 3.7 | 3.6 / 3.6 | 0.0 / 0.0 | gemma4:12b-it-qat (ctx 8192) |
| enrutado | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | gemma4:12b-it-qat (ctx 8192) |

## Cargas de modelo por reseña (resto)

| Modelo | Cargas por reseña (mediana) | De ellas, en la precarga de `require_gpu` | Tiempo por carga (mediana / p90) |
|---|---|---|---|
| `qwen3.6:27b-q4_K_M` | 1 | 1 | 22.0 / 22.3 |
| `gemma4:12b-it-qat` | 1 | 1 | 9.0 / 9.0 |
| `bge-m3` | 1 | 0 | 2.3 / 2.3 |

## Inferencia por llamada (resto)

| Etapa | Tokens de entrada | Tokens generados | prompt_eval (s) | eval (s) |
|---|---|---|---|---|
| analisis | 271 | 221 | 0.5 / 0.6 | 5.6 / 9.4 |
| respuesta | 1873 | 127 | 1.9 / 2.1 | 3.2 / 3.5 |
| juez | 1331 | 212 | 0.7 / 0.7 | 2.9 / 2.9 |

## Arranque (una vez por sesión de la app)

- Carga del clasificador (3 × mRoBERTa en CPU): 8.5 s.
- `warm_up_juez` (con los modelos descargados): 8.1 / 8.7 s (n = 3).
- `warm_up_generador` (con los modelos descargados): 17.8 / 17.9 s (n = 3).

## Destino observado frente a la cola cacheada

Todas las reseñas acabaron con el mismo destino que en la cola cacheada.

## Juez asíncrono (variante A) frente a la base

Ejecución de A: `latencia_v6_A_20261029-2234.jsonl` (15 reseñas sin contar la primera de cada repetición). Mediana / p90 [mínimo–máximo] en segundos. Diferencia = base − A, con IC 95 % bootstrap pareado (10000 remuestras); con n tan pequeño, el IC es orientativo.

| Reseñas | n | Visible en base | Visible en A | Ahorro hasta ver el borrador (IC 95 %) | Hasta el veredicto (A) |
|---|---|---|---|---|---|
| Todas | 15 | 48.2 / 52.2 [43.8–52.9] | 35.6 / 39.6 [31.2–40.2] | 12.6 (12.6–12.6) | 48.2 / 52.2 [43.8–52.9] |
| Destino publicable | 6 | 48.0 / 51.1 [46.5–51.2] | 35.4 / 38.4 [33.9–38.6] | 12.6 (12.6–12.7) | 48.0 / 51.1 [46.5–51.2] |
| Destino revisión humana | 9 | 48.6 / 52.5 [43.8–52.9] | 36.0 / 39.8 [31.2–40.2] | 12.6 (12.6–12.7) | 48.6 / 52.5 [43.8–52.9] |

Control (independientes): tiempo hasta el veredicto en A (48.2 / 52.2) frente a la base `latencia_v6_20261029-2148.jsonl` (49.0 / 53.0); diferencia de medianas A − base -0.8 s (IC 95 % -3.3 a +2.3). A no cambia el trabajo, solo cuándo se muestra el borrador.

## Todas las mediciones (results/latencia_*.jsonl)

Reseñas sin contar la primera de cada repetición. Cargas del generador por reseña: 2 indica la doble carga (precarga con otro contexto y recarga en el análisis).

| Fichero | Fecha | Ollama | Prompt | Variante | n | Total | Carga | % carga | Cargas del generador |
|---|---|---|---|---|---|---|---|---|---|
| `latencia_v6_20261029-2115.jsonl` | 2026-10-29T21:15 | 0.40.8 | v6 | base | 15 | 75.1 | 58.8 | 78% | 2 |
| `latencia_v6_20261029-2148.jsonl` | 2026-10-29T21:48 | 0.40.8 | v6 | base | 15 | 49.0 | 33.5 | 67% | 1 |
| `latencia_v6_A_20261029-2234.jsonl` | 2026-10-29T22:34 | 0.40.8 | v6 | A | 15 | 48.2 | 33.2 | 66% | 1 |

## Limitaciones

- Muestra pequeña (6 reseñas, 15 medidas sin contar la primera de cada repetición): las cifras sirven para ver el orden de magnitud de carga frente a inferencia, no para afinar milisegundos.
- Caché de páginas del sistema: con 32 GB de RAM, los ficheros de los modelos quedan en memoria tras la primera carga, así que las recargas miden RAM → VRAM, no disco. Es lo que ocurre en la demo; un arranque desde disco solo se mediría tras reiniciar.
- La caché de prefijos de Ollama sigue activa (como en la demo): los prompts de sistema repetidos pueden evaluarse más rápido cuando el modelo sigue cargado.
- Se mide `pipeline.run`; la interfaz de Gradio añade su propio tiempo (pequeño).
- Las cifras dependen de la versión de Ollama (0.40.8) y de su llama.cpp.
