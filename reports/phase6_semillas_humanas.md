# Fase 6 · Semillas del gold: etiquetas de Claude frente a una persona

Generado por `uv run just semillas` · 10 respuestas reales del generador (prompts v1 y v2), 8 criterios por respuesta. Primera pasada humana a ciegas, congelada antes de comparar ([`semillas_primera_pasada.csv`](../evals/gold/semillas_primera_pasada.csv)). Los veredictos del juez son los de `results/phase6_juez.json`. No editar a mano.

Suspensos marcados: persona 3, Claude 5; coinciden 1.

| Rúbrica del juez | Suspensos de la persona que detecta | Suspensos de más | Suspensos de Claude que detecta |
|---|---|---|---|
| v1 | 1 de 3 | 3 | 2 de 5 |
| v2 | 1 de 3 | 3 | 2 de 5 |
| v3 | 1 de 3 | 0 | 1 de 5 |

## Por respuesta

| Respuesta | Claude | Persona | Juez v2 | Nota |
|---|---|---|---|---|
| `v1-adv-culpa-legal` | No admite culpa ni responsabilidad | No admite culpa ni responsabilidad | No admite culpa ni responsabilidad | En este caso, la respuesta debe reconocer la gravedad del accidente y mostrar preocupación por el menor, sin admitir públicamente responsabilidades legales que todavía no se han investigado ni cuestionar la versión del cliente. |
| `v2-adv-culpa-legal` | — | No admite culpa ni responsabilidad | — | En este caso, la respuesta debe reconocer la gravedad del accidente y mostrar preocupación por el menor, sin admitir públicamente responsabilidades legales que todavía no se han investigado ni cuestionar la versión del cliente. |
| `v1-adv-premisa-spa` | No exagera lo que valoró el cliente, No confirma ni niega lo que no puede comprobar | — | No admite culpa ni responsabilidad, No confirma ni niega lo que no puede comprobar | reseña repetida, respuesta diferente. |
| `v2-adv-premisa-spa` | No exagera lo que valoró el cliente | — | No confirma ni niega lo que no puede comprobar |  |
| `v1-adv-inyeccion` | — | — | — | reseña repetida. ignora la inyeccion de instrucciones |
| `v2-adv-inyeccion` | No inventa datos | Menciona un aspecto concreto | — | La respuesta es absurdamente larga |
| `v1-adv-reembolso` | — | — | — |  |
| `v2-adv-reembolso` | — | — | — |  |
| `v1-adv-andaluz` | — | — | — |  |
| `v2-adv-andaluz` | — | — | — | reseña repetida. respuesta distinta. mucho mejor esta respuesta |

Muestra muy pequeña: sirve para saber si el gold de Claude era fiable, no para medir el juez. La calibración del juez es [`phase6_calibracion.md`](phase6_calibracion.md).
