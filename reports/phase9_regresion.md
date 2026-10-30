# Fase 9 · Regresión de prompts en las mismas condiciones

Generado por `uv run just regresion` · generador `qwen3.6:27b-q4_K_M` · juez `gemma4:12b-it-qat` con rúbrica `v2h` y ficha · pipeline actual (detector de trampas v2, `kb/` actual) sobre los 54 casos de la demostración (14 sintéticos, 40 reales del AHR). No editar a mano.

## Suspensos del juez por criterio

| Criterio | v6 | v8 | v9 |
|---|---|---|---|
| Menciona un aspecto concreto | 0 | 0 | 0 |
| No promete compensaciones | 0 | 0 | 0 |
| No admite culpa ni responsabilidad | 11 | 17 | 15 |
| No confirma ni niega lo que no puede comprobar | 1 | 2 | 2 |
| No inventa datos | 0 | 2 | 0 |
| No exagera lo que valoró el cliente | 0 | 0 | 0 |
| Español estándar y de usted | 0 | 0 | 0 |
| Tono cordial, sin culpar al cliente | 2 | 2 | 2 |

## Resumen

| | v6 | v8 | v9 |
|---|---|---|---|
| Reales que cumplen todo | 34/40 | 28/40 | 29/40 |
| Publicables (enrutado de producción) | 8 | 10 | 7 |
| Reseñas trampa | 1 | 1 | 1 |
| Empiezan con «Estimado/a…» | 53/53 | 53/53 | 0/53 |
| Primera frase más repetida | «Muchas gracias por compartir su…» (17) | «Gracias por compartir su opinión.…» (9) | «Lamentamos que su experiencia no…» (17) |

## Por pares frente a v6 (los dos órdenes; lo inconsistente, empate)

- v8: gana 4, pierde 28, empata 22.
- v9: gana 3, pierde 26, empata 25.

## Criterio automático de adopción de v9

- «No admite culpa»: v9 15 frente a v6 11 → NO cumple.
- Por pares frente a v6: PIERDE (3 a 26).
- **No pasa** la parte automática. Falta la valoración humana de reseñas nuevas (no las 42 con las que se escribió v9).
