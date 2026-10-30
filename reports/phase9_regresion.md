# Fase 9 · Regresión de prompts en las mismas condiciones

Generado por `uv run just regresion` · generador `qwen3.6:27b-q4_K_M` · juez `gemma4:12b-it-qat` con rúbrica `v2i` y ficha · pipeline actual (detector de trampas v2, `kb/` actual) sobre los 54 casos de la demostración (14 sintéticos, 40 reales del AHR). No editar a mano.

## Suspensos del juez por criterio

| Criterio | v6 | v9 |
|---|---|---|
| Menciona un aspecto concreto | 0 | 0 |
| No promete compensaciones | 0 | 0 |
| No admite culpa ni responsabilidad | 11 | 9 |
| No confirma ni niega lo que no puede comprobar | 1 | 1 |
| No inventa datos | 1 | 1 |
| No exagera lo que valoró el cliente | 0 | 1 |
| Español estándar y de usted | 0 | 0 |
| Tono cordial, sin culpar al cliente | 2 | 0 |

## Resumen

| | v6 | v9 |
|---|---|---|
| Reales que cumplen todo | 34/40 | 30/40 |
| Publicables (enrutado de producción) | 8 | 3 |
| Reseñas trampa | 1 | 1 |
| Empiezan con «Estimado/a…» | 53/53 | 0/53 |
| Empiezan con Hola · Saludos | Hola 0 · Saludos 0 | Hola 28 · Saludos 25 |
| Finalidad recortada tras «revisaremos» | 0/53 | 15/53 |
| Primera frase más repetida (tras el saludo) | «Muchas gracias por compartir su…» (17) | «Lamentamos que su experiencia no…» (16) |

## Por pares frente a v6 (juez de pares v2: el saludo no cuenta; los dos órdenes; lo inconsistente, empate)

Puertas (canaries escritos a mano). Pares: usted frente a tuteo → «A» (debe ser A, el usted); «Hola:» frente a «Estimado cliente:» con el mismo texto → «empate» (no debe ser B). Rúbrica v2i, registro: «Hola:» con usted cumple (debe cumplir); tuteo no cumple (no debe cumplir). **Pasan**.

- v9: gana 10, pierde 26, empata 18.

## Filtro de seguridad para adoptar v9

v9 no puede suspender más que v6 en estos criterios (el resto se informa arriba, pero decide la valoración humana a ciegas de reseñas nuevas):

- No promete compensaciones: v9 0 frente a v6 0 → cumple.
- No inventa datos: v9 1 frente a v6 1 → cumple.
- No confirma ni niega lo que no puede comprobar: v9 1 frente a v6 1 → cumple.

**Pasa** el filtro. Siguiente paso: valoración a ciegas de las tandas, v6 frente a v9.
