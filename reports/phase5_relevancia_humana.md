# Fase 5 · Relevancia: etiquetas de Claude frente a una persona

Generado por `uv run just relevancia` · 30 consultas **sintéticas** redactadas por Claude. Primera pasada humana a ciegas, congelada antes de comparar ([`relevancia_primera_pasada.csv`](../evals/retrieval/relevancia_primera_pasada.csv)). No editar a mano.

## Politicas (17 documentos; el prompt toma 5)

Acuerdo con Claude: kappa **0.85** · 21 de 30 consultas idénticas · Jaccard medio 0.84 · relevantes marcados: Claude 43, persona 43.

Consultas sin ningún relevante: Claude 0, persona 0. Según la persona, de los 150 documentos que el pipeline (hibrida) entregaría al prompt, 35 son relevantes.

| Etiquetas | Método | n | recall@1 | recall@3 | recall@5 | mrr |
|---|---|---|---|---|---|---|
| Claude | bm25 | 30 | 0.44 | 0.69 | 0.77 | 0.69 |
| Claude | densa | 30 | 0.43 | 0.77 | 0.84 | 0.72 |
| Claude | hibrida | 30 | 0.58 | 0.77 | 0.89 | 0.82 |
| Persona | bm25 | 30 | 0.42 | 0.68 | 0.78 | 0.67 |
| Persona | densa | 30 | 0.44 | 0.78 | 0.85 | 0.72 |
| Persona | hibrida | 30 | 0.54 | 0.78 | 0.87 | 0.78 |

Diferencias pareadas con etiquetas de la persona (IC 95 %, bootstrap):

- hibrida − densa, mrr: +0.06 (-0.05 a +0.18)
- hibrida − densa, recall@5: +0.02 (-0.09 a +0.12)
- hibrida − bm25, mrr: +0.12 (-0.01 a +0.24)
- hibrida − bm25, recall@5: +0.09 (-0.05 a +0.24)

### Desacuerdos (9)

| Consulta | Claude | Persona | Nota |
|---|---|---|---|
| `adv-reembolso` | pol-averias, pol-compensaciones, pol-reembolsos | pol-averias, pol-compensaciones, pol-limpieza, pol-personal, pol-precio, pol-reembolsos |  |
| `adv-premisa-spa` | pol-servicios | pol-elogios, pol-servicios |  |
| `adv-4estrellas-queja` | pol-averias, pol-elogios | pol-averias |  |
| `adv-ambigua` | pol-elogios, pol-ruido | pol-personal, pol-ruido |  |
| `q01` | pol-compensaciones, pol-reembolsos | pol-reembolsos |  |
| `q02` | pol-averias, pol-incidentes | pol-incidentes |  |
| `q03` | pol-reembolsos | pol-compensaciones, pol-reembolsos |  |
| `q06` | pol-elogios, pol-personal | pol-personal |  |
| `q21` | pol-compensaciones, pol-ruido | pol-compensaciones |  |

## Respuestas (16 documentos; el prompt toma 2)

Acuerdo con Claude: kappa **0.64** · 18 de 30 consultas idénticas · Jaccard medio 0.60 · relevantes marcados: Claude 33, persona 16.

Consultas sin ningún relevante: Claude 2, persona 14. Según la persona, de los 60 documentos que el pipeline (densa) entregaría al prompt, 14 son relevantes.

| Etiquetas | Método | n | recall@1 | recall@3 | recall@2 | mrr |
|---|---|---|---|---|---|---|
| Claude | bm25 | 28 | 0.25 | 0.64 | 0.41 | 0.48 |
| Claude | densa | 28 | 0.55 | 0.91 | 0.79 | 0.77 |
| Claude | hibrida | 28 | 0.39 | 0.82 | 0.61 | 0.63 |
| Persona | bm25 | 16 | 0.25 | 0.69 | 0.44 | 0.46 |
| Persona | densa | 16 | 0.75 | 0.94 | 0.88 | 0.84 |
| Persona | hibrida | 16 | 0.50 | 0.81 | 0.69 | 0.66 |

Diferencias pareadas con etiquetas de la persona (IC 95 %, bootstrap):

- hibrida − densa, mrr: -0.18 (-0.35 a -0.04)
- hibrida − densa, recall@2: -0.19 (-0.44 a +0.06)
- hibrida − bm25, mrr: +0.21 (+0.05 a +0.35)
- hibrida − bm25, recall@2: +0.25 (+0.00 a +0.50)

### Desacuerdos (12)

| Consulta | Claude | Persona | Nota |
|---|---|---|---|
| `adv-4estrellas-queja` | resp-wifi | — |  |
| `adv-ambigua` | resp-correcto, resp-ruido | — |  |
| `q01` | resp-reembolso | — |  |
| `q03` | resp-reembolso | — |  |
| `q06` | resp-dialecto, resp-elogio | — |  |
| `q08` | resp-aire-consumo, resp-wifi | — |  |
| `q09` | resp-aire-consumo, resp-wifi | — |  |
| `q10` | resp-aire-consumo | — |  |
| `q19` | resp-elogio | — |  |
| `q20` | resp-correcto | — |  |
| `q21` | resp-reembolso, resp-ruido | — |  |
| `q22` | resp-caida | — |  |

