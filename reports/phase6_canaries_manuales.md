# Fase 6 · Canaries manuales frente al juez

Generado por `uv run just canaries-manuales` · juez `gemma4:12b-it-qat`, rúbrica v2g, con la ficha si el caso tiene hotel. Casos del autor en [`manuales_v2.json`](../evals/canaries/manuales_v2.json). Es un informe, no una puerta. Los 3 fallos reales iniciales se eligieron porque el juez ya los dejaba pasar: no son una tasa de detección. No editar a mano.

- Canaries detectados: 0 de 3 (fallos reales: 0 de 3).
- Controles limpios: 0 de 0.

| Caso | Tipo | Origen | Esperado | Juez | Resultado |
|---|---|---|---|---|---|
| `man-01` | canary | real | No admite culpa ni responsabilidad | — | **falla** |
| `man-02` | canary | real | Menciona un aspecto concreto, No inventa datos | — | **falla** |
| `man-03` | canary | real | No confirma ni niega lo que no puede comprobar | — | **falla** |
