# Guía de la demo

Dos partes: **repetición** (reseñas ya evaluadas y contestadas, sin modelos) y, si alguien lo pide,
**prueba en vivo** desde el PC con la GPU.

## 1. Repetición

En línea: <https://javiromano.github.io/Spanish-hotel-review-LLM/> (GitHub Pages, carpeta `docs/`
de `main`). Es una página estática con los datos dentro: funciona sin servidor y sin conexión
abriendo `docs/index.html`.

```bash
uv run just replay        # regenera docs/index.html y la abre; después, commit + push para publicarla
uv run --with playwright python scripts/verificar_replay.py   # capturas (docs/screenshots/), consola, contraste AA, teclado
```

La plantilla es `scripts/replay_template.html`. El botón «Pedir prueba en vivo» enlaza al perfil de
LinkedIn (`LINKEDIN` en `scripts/build_replay.py`). Cada caso tiene su enlace directo
(`…/#rag-carteles`).

15 casos: 6 reseñas propias (con **qué se esperaba**, escrito antes de generar, y la
**valoración del autor**, [`evals/demo/valoracion_propias.json`](../evals/demo/valoracion_propias.json))
y 9 ilustrativos (con una **nota** escrita después de leer la respuesta;
[`evals/demo/seleccion_replay.json`](../evals/demo/seleccion_replay.json)).

### Recorrido guiado (6–8 minutos)

Está dentro de la página: botón **«▶ Recorrido guiado»**, 9 pasos con las flechas. Los pasos y su
texto salen de `recorrido` en `seleccion_replay.json`:

1. `p18` · línea base: una positiva sin trampas se publica sola.
2. `adv-4estrellas-queja` · RAG: la explicación del wifi sale de la ficha.
3. `ahr-ahr-7499` · umbral: buena respuesta, confianza 0,849 < 0,85, a una persona.
4. `adv-premisa-spa` · premisa falsa: informa de la ficha sin dar la razón ni acusar.
5. `p02` · instrucciones ocultas: se detectan y no se obedecen (aunque la respuesta descarta
   también las quejas reales: por eso pasa por una persona).
6. `vampiros` · una reseña absurda: se detecta como trampa y se responde con ironía breve.
7. `adv-reembolso` · el juez detecta una admisión implícita de culpa.
8. `rag-carteles` · lo que el juez no ve; la regla de accidentes la manda a una persona.
9. `p08` · fallo reconocido: el juez lo aprueba (8/8) y el autor lo valora «no cumple».

Cierre: el sistema no pretende publicar solo. Publica lo seguro (positivas claras) y, para lo demás,
entrega un borrador con los motivos por los que necesita una persona. El paso 9 lo demuestra: el
juez no basta, y por eso lo serio nunca se publica sin revisión.

### Si preguntan

- **¿Por qué «Estimado cliente» en todas?** Es un problema conocido. Una versión que lo corregía
  (v9) perdió en la valoración humana a ciegas y ante el juez: README, «Versiones del prompt
  posteriores a v6».
- **¿Cuánto tarda?** ~49 s por reseña en vivo; el borrador se ve a los ~36 s y el juez llega después.
- **¿Sale algún dato del equipo?** No: todo corre en local (Ollama + GPU AMD).

## 2. Prueba en vivo (cuando alguien la pide por LinkedIn)

1. Acordar día y hora. Avisar: una reseña tarda ~1 minuto, y lo que escriba se guarda sin su nombre.
2. Comprobar la GPU: `uv run just gpu-ollama` (si Ollama se actualizó, reinstalar el zip de ROCm de
   esa versión; ver CLAUDE.md §7).
3. Usuario y contraseña de la sesión como variables de entorno, nunca en el comando ni en el código:
   `DEMO_USER` y `DEMO_PASS` (por ejemplo, variables de usuario de Windows; una contraseña nueva por
   sesión).
4. `uv run just app-live` y, en otra terminal, `cloudflared tunnel --url http://127.0.0.1:7860`.
5. Enviar el enlace del túnel y la contraseña por mensaje privado (no en público).
6. Al terminar: cerrar el túnel y la app, descargar los modelos (`ollama stop …`) y cambiar la
   contraseña.
7. Después: valorar las respuestas con `scripts/notas_vivo.py`. Las reseñas quedan en `data/live/`
   (fuera de git) y nunca pasan por la caché de `results/`.
