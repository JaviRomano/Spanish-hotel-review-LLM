# Guía de la demo

Dos partes: **repetición** (reseñas ya evaluadas y contestadas, sin modelos) y, si alguien lo pide,
**prueba en vivo** desde el PC con la GPU.

## 1. Repetición

```bash
uv run just replay        # reconstruye demo_replay/casos.json y abre http://127.0.0.1:7861
```

El aviso de la cabecera enlaza al perfil de LinkedIn (`LINKEDIN` en `demo_replay/app.py`) para
pedir la prueba en vivo.

18 casos: las 10 reseñas propias (con **qué se esperaba**, escrito antes de generar) y 8 de la
demostración (con una **nota** escrita después de leer la respuesta;
[`evals/demo/seleccion_replay.json`](../evals/demo/seleccion_replay.json)).

### Recorrido recomendado (6–8 minutos)

| # | Caso | Qué enseña |
|---|---|---|
| 1 | `p18` · control positivo | La línea base: una reseña positiva sin trampas se publica sola. |
| 2 | `adv-4estrellas-queja` | El RAG: la explicación del wifi sale de la ficha del hotel, no del modelo. Publicable. |
| 3 | `ahr-ahr-7499` · real, 4★ | El umbral: buena respuesta, pero la confianza (0,849) no llega a 0,85 y pasa a una persona. |
| 4 | `p06` · sarcasmo | El clasificador cree que es positiva (0,93); el LLM ve la queja. Si no coinciden, a revisión. |
| 5 | `adv-premisa-spa` | Premisa falsa: informa de lo que dice la ficha sin dar la razón ni acusar al cliente. |
| 6 | `p02` · instrucciones ocultas | La trampa se detecta y no se obedece. Pero la respuesta descarta también las quejas reales que traía la reseña: por eso pasa por una persona. |
| 7 | `adv-reembolso` | El juez detecta una admisión implícita («prioridad absoluta, por lo que revisaremos»). |
| 8 | `rag-carteles` | **Lo que el juez no ve**: «para garantizar la seguridad…» sugiere culpa y el juez lo aprueba. Por eso los accidentes siempre van a una persona. |

Cierre: el sistema no pretende publicar solo. Publica lo seguro (positivas claras) y, para lo demás,
entrega un borrador con los motivos por los que necesita una persona.

### Si preguntan

- **¿Por qué «Estimado cliente» en todas?** Es un problema conocido. Una versión que lo corregía
  (v9) perdió en la valoración humana a ciegas y ante el juez: README, «Versiones del prompt
  posteriores a v6».
- **¿Por qué castellano si la reseña está en valenciano/catalán/gallego?** Decisión de diseño: las
  respuestas van siempre en castellano estándar (el «qué se esperaba» de algunas reseñas propias se
  escribió antes de tomarla).
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
