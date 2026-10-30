# Fase 9 · Comparación humana a ciegas de dos versiones del prompt

Generado por `uv run python scripts/comparacion_ciegas.py resultado --tag ciegas_t01-03 --informe reports/phase9_ciegas.md`. No editar a mano.

- 30 reseñas nuevas escritas a mano (no son casos de desarrollo), respondidas con las dos versiones en las mismas condiciones. Las reseñas, las respuestas y las valoraciones quedan fuera de git (`data/live/`): aquí solo van los recuentos.
- Valora una persona. Cada reseña muestra las dos respuestas como A y B en orden aleatorio, con ids opacos y sin el saludo (delataba la versión).

| | tandas_01-03_v6 | tandas_01-03_v9 |
|---|---|---|
| Preferida | 15 | 10 |
| Publicable tal cual | 8/30 | 4/30 |

- Empates: 3; sin valorar: 2. Publicables las dos: 1.
- Prueba de signos exacta (bilateral, sin empates): p = 0.42. Con 25 comparaciones decididas, solo una preferencia muy clara sería significativa por sí sola.
