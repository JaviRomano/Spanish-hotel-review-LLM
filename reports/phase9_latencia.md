# Fase 9 · Latencia por etapa (uso interactivo)

Generado por `uv run just latencia` a partir de `results/latencia_v6_20261029-2115.jsonl`. No editar a mano.

- Fecha: 2026-10-29T21:15:54 · Ollama 0.40.8
- Generador `qwen3.6:27b-q4_K_M` (prompt v6) · juez `gemma4:12b-it-qat` (rúbrica v2g) · embeddings `bge-m3` · clasificador mRoBERTa (3 semillas, CPU)
- Muestra: `evals/latencia/muestra_v1.json`, 6 reseñas × 3 repeticiones = 18 medidas. Cada repetición descarga todos los modelos, precarga juez y generador (como la app) y procesa las reseñas una a una.
- Sin caché de resultados: 0 llamadas al LLM salieron de la caché (correcto: todas se midieron).

Cifras: **mediana / p90 en segundos**. Con tan pocas medidas el p90 es casi el máximo.

## ¿Cuánto es carga y cuánto inferencia?

Carga = `load_duration` de las llamadas a Ollama más el tiempo de pared de la precarga de `require_gpu` (un generate con el prompt vacío que carga el modelo pero devuelve las métricas a cero). Inferencia = `prompt_eval_duration` + `eval_duration`. Resto = clasificador en CPU, normalización, comprobaciones y comunicación con Ollama.

| Reseñas | n | Total | Carga | Inferencia | Resto | % carga (suma) |
|---|---|---|---|---|---|---|
| Primera de cada repetición | 3 | 56.2 / 57.4 | 42.2 / 43.1 | 13.5 / 13.7 | 0.5 / 0.6 | 75% |
| Resto | 15 | 75.1 / 77.4 | 58.8 / 60.2 | 14.9 / 18.5 | 0.5 / 0.7 | 78% |
| Resto · destino publicable | 6 | 74.6 / 76.4 | 58.7 / 59.8 | 15.7 / 17.3 | 0.6 / 0.6 | 78% |
| Resto · destino revisión humana | 9 | 75.1 / 78.0 | 58.8 / 60.2 | 14.9 / 18.6 | 0.5 / 0.7 | 78% |

## Tiempo de pared por etapa

| Etapa | Primera reseña | Resto | Carga en la etapa (resto) | Modelos en VRAM al acabar |
|---|---|---|---|---|
| normalizacion | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | gemma4:12b-it-qat |
| clasificador | 0.1 / 0.1 | 0.1 / 0.3 | 0.0 / 0.0 | gemma4:12b-it-qat |
| embeddings | 2.5 / 2.5 | 2.4 / 2.5 | 2.3 / 2.3 | gemma4:12b-it-qat |
| carga_generador | 0.0 / 0.0 | 21.7 / 22.0 | 21.7 / 22.0 | qwen3.6:27b-q4_K_M |
| analisis | 26.3 / 26.4 | 23.6 / 27.1 | 17.1 / 17.3 | qwen3.6:27b-q4_K_M |
| respuesta | 5.6 / 5.8 | 5.2 / 5.6 | 0.0 / 0.0 | qwen3.6:27b-q4_K_M |
| checks | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | qwen3.6:27b-q4_K_M |
| carga_juez | 8.8 / 9.3 | 8.9 / 9.1 | 8.9 / 9.1 | gemma4:12b-it-qat |
| juez | 12.7 / 13.2 | 12.8 / 13.1 | 9.2 / 9.4 | gemma4:12b-it-qat |
| enrutado | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | gemma4:12b-it-qat |

## Cargas de modelo por reseña (resto)

| Modelo | Cargas por reseña (mediana) | De ellas, en la precarga de `require_gpu` | Tiempo por carga (mediana / p90) |
|---|---|---|---|
| `qwen3.6:27b-q4_K_M` | 2 | 1 | 17.3 / 21.7 |
| `gemma4:12b-it-qat` | 2 | 1 | 9.1 / 9.4 |
| `bge-m3` | 1 | 0 | 2.3 / 2.3 |

## Inferencia por llamada (resto)

| Etapa | Tokens de entrada | Tokens generados | prompt_eval (s) | eval (s) |
|---|---|---|---|---|
| analisis | 271 | 221 | 0.5 / 0.6 | 5.6 / 9.4 |
| respuesta | 1873 | 127 | 1.9 / 2.1 | 3.2 / 3.5 |
| juez | 1331 | 212 | 0.7 / 0.7 | 2.9 / 3.0 |

## Arranque (una vez por sesión de la app)

- Carga del clasificador (3 × mRoBERTa en CPU): 7.9 s.
- `warm_up_juez` (con los modelos descargados): 8.2 / 8.7 s (n = 3).
- `warm_up_generador` (con los modelos descargados): 18.0 / 18.1 s (n = 3).

## Destino observado frente a la cola cacheada

Todas las reseñas acabaron con el mismo destino que en la cola cacheada.

## Limitaciones

- Muestra pequeña (6 reseñas, 15 medidas sin contar la primera de cada repetición): las cifras sirven para ver el orden de magnitud de carga frente a inferencia, no para afinar milisegundos.
- Caché de páginas del sistema: con 32 GB de RAM, los ficheros de los modelos quedan en memoria tras la primera carga, así que las recargas miden RAM → VRAM, no disco. Es lo que ocurre en la demo; un arranque desde disco solo se mediría tras reiniciar.
- La caché de prefijos de Ollama sigue activa (como en la demo): los prompts de sistema repetidos pueden evaluarse más rápido cuando el modelo sigue cargado.
- Se mide `pipeline.run`; la interfaz de Gradio añade su propio tiempo (pequeño).
- Las cifras dependen de la versión de Ollama (0.40.8) y de su llama.cpp.
