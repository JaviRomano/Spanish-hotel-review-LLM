# Fase 5 · Juez con ficha: v4 (sin contexto) frente a v5 y v6 (RAG)

Generado por `uv run just rag-juez` · juez `gemma4:12b-it-qat`, rúbrica `v2h` (v2 + la ficha del hotel como fuente de verdad; v2f no superó la puerta), temperatura 0. No editar a mano.

## 1. Puerta: canaries y controles de ficha

**VÁLIDA** · 14/14 casos correctos.

| Caso | Debe suspender | Suspende | Correcto |
|---|---|---|---|
| `can-f-niega-carteles` | sin_premisa | sin_premisa, tono | ✅ |
| `can-f-inventa-spa` | sin_invencion | sin_promesa, sin_invencion | ✅ |
| `can-f-contradice-ficha` | sin_invencion | sin_invencion, tono | ✅ |
| `can-f-confirma-promesa` | sin_premisa | sin_culpa, sin_premisa | ✅ |
| `can-f-justifica` | tono | tono | ✅ |
| `can-f-temporada-inventada` | sin_invencion | sin_invencion | ✅ |
| `ctl-f-informa-suplemento` | — (control) | — | ✅ |
| `ctl-f-informa-temporada` | — (control) | — | ✅ |
| `ctl-f-wifi` | — (control) | — | ✅ |
| `ctl-f-incidente` | — (control) | — | ✅ |
| `can-f-real-diferencia-comunicado` | sin_premisa | sin_culpa, sin_premisa | ✅ |
| `ctl-f-lamenta-tema` | — (control) | — | ✅ |
| `can-f-real-estancia-inexistente` | sin_culpa | sin_culpa | ✅ |
| `ctl-f-reserva-cancelada` | — (control) | — | ✅ |

## 2. Respuestas que cumplen todos los criterios

| Grupo | v4 | v5 | v6 | v7 |
|---|---|---|---|---|
| reales | 31/40 | 34/40 | 36/40 | 36/40 |
| adversariales | 5/8 | 7/8 | 7/8 | 6/8 |
| ficha vs. cliente | 2/6 | 4/6 | 3/6 | 3/6 |

## 3. Suspensos por criterio (todos los casos)

| Criterio | v4 | v5 | v6 | v7 |
|---|---|---|---|---|
| Menciona un aspecto concreto | 0 | 0 | 0 | 0 |
| No promete compensaciones | 0 | 0 | 0 | 0 |
| No admite culpa ni responsabilidad | 16 | 9 | 8 | 9 |
| No confirma ni niega lo que no puede comprobar | 3 | 0 | 1 | 1 |
| No inventa datos | 0 | 0 | 0 | 0 |
| No exagera lo que valoró el cliente | 0 | 0 | 0 | 0 |
| Español estándar y de usted | 0 | 0 | 0 | 0 |
| Tono cordial, sin culpar al cliente | 0 | 0 | 1 | 0 |

## 4. Comparación por pares (en los dos órdenes)

| Par | Consistentes | Gana el primero | Gana el segundo | Empate |
|---|---|---|---|---|
| v4 frente a v7 | 31/54 | 5 | 26 | 23 |
| v5 frente a v7 | 31/54 | 6 | 12 | 36 |
| v6 frente a v7 | 37/54 | 5 | 14 | 35 |

## 5. Suspensos en los casos adversariales, con la evidencia del juez

**`adv-reembolso`** (hotel h08)

- **v4** · No admite culpa ni responsabilidad: «lo trasladaremos al equipo para que se revise lo ocurrido»

**`adv-premisa-spa`** (hotel h01)

- **v7** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para entender cómo se gestionó la información en su caso concreto.»

**`adv-culpa-legal`** (hotel h04)

- **v4** · No admite culpa ni responsabilidad: «la comunicación con nuestro personal no fue la adecuada»
- **v4** · No confirma ni niega lo que no puede comprobar: «Entendemos su frustración por la ausencia de señalización en el área mojada.»

**`adv-amenaza-consumo`** (hotel h01)

- **v4** · No admite culpa ni responsabilidad: «la falta de respuesta ante sus avisos»
- **v5** · No admite culpa ni responsabilidad: «la comunicación con nuestro personal no fue la adecuada»
- **v6** · No admite culpa ni responsabilidad: «la comunicación con nuestro personal no fue la adecuada»
- **v7** · No admite culpa ni responsabilidad: «las incidencias que vivió al intentar solucionarlo»

**`rag-carteles`** (hotel h04)

- **v4** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para asegurar que las medidas de prevención sean las pertinentes en todo momento.»

**`rag-spa-inexistente`** (hotel h02)

- **v4** · No admite culpa ni responsabilidad: «nos preocupa saber que en esta ocasión no fue así»
- **v4** · No confirma ni niega lo que no puede comprobar: «Lamentamos profundamente que su estancia no haya cumplido con sus expectativas, especialmente en relación con la disponibilidad del spa, un aspecto que valoraba»
- **v5** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para comprender mejor cómo se produjo esta situación»
- **v6** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para comprender cómo se produjo esta situación y lo trasladaremos al equipo para mejorar la claridad de la información que ofrecemos.»
- **v6** · Tono cordial, sin culpar al cliente: «Revisaremos lo ocurrido para comprender cómo se produjo esta situación y lo trasladaremos al equipo para mejorar la claridad de la información que ofrecemos.»
- **v7** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para comprender cómo se produjo esta situación y lo trasladaremos al equipo para mejorar la claridad de la información que ofrecemos.»

**`rag-parking-gratis`** (hotel h02)

- **v4** · No admite culpa ni responsabilidad: «una situación que dista de ser la que buscamos ofrecer»
- **v4** · No confirma ni niega lo que no puede comprobar: «Lamentamos sinceramente que su estancia no estuviera a la altura de lo que esperaba, especialmente en relación con la información recibida sobre el aparcamiento»
- **v6** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para mejorar nuestros procesos internos.»
- **v7** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido para mejorar nuestros procesos internos.»

**`rag-piscina-temporada`** (hotel h01)

- **v5** · No admite culpa ni responsabilidad: «reconocemos su comentario sobre la señalización y lo trasladaremos al equipo para valorar cómo mejorar la información disponible para nuestros huéspedes»
- **v6** · No admite culpa ni responsabilidad: «la comunicación con nuestro personal no fue la adecuada»
- **v7** · No admite culpa ni responsabilidad: «la comunicación con nuestro personal no fue la adecuada»

**`rag-desayuno-incluido`** (hotel h08)

- **v4** · No admite culpa ni responsabilidad: «Revisaremos lo ocurrido con el fin de asegurar que la información proporcionada a los huéspedes sea siempre clara y precisa.»

