# Uso: `uv run just <receta>` (uv activa el entorno, así que aquí no se llama a uv).
# Instalar/actualizar el entorno: `uv sync` (en WSL2 incluye torch ROCm).
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    @just --list

# Tests
test:
    python -m pytest

# Linter y formato
lint:
    ruff check src tests scripts
    ruff format --check src tests scripts

fmt:
    ruff format src tests scripts
    ruff check --fix src tests scripts

# Comprueba que data/raw no ha cambiado
check-raw:
    python -m caso_uso_llm.raw_integrity

# Comprueba la GPU AMD con ROCm (solo en WSL2)
gpu:
    python scripts/check_gpu.py

# Descarga los datasets de terceros (requiere `hf auth login` y aceptar sus términos en HF)
data-download:
    python -m caso_uso_llm.data.download

# Pipeline de datos: crudo -> data/processed + reports/data_report.md
data:
    python -m caso_uso_llm.data.build

# Fase 3: baseline TF-IDF + LR (opciones A, A_sin_trad, B) -> results/ + reports/
baseline:
    python -m caso_uso_llm.classify.baseline

# Fase 3: fine-tuning de RoBERTa-BNE (solo WSL2). Ej.: just train --options B,C --seeds 42
train *ARGS:
    python -m caso_uso_llm.classify.finetune {{ARGS}}

# Fase 3b: evaluación realista (estrés, SFU, cobertura vs error) del ensamble A (solo WSL2)
realista:
    python -m caso_uso_llm.classify.realistic

# Fase 3: referencia zero-shot con el LLM local (Ollama) + prueba de presión (sycophancy)
zeroshot:
    python -m caso_uso_llm.classify.zeroshot

# Fase 4: aspectos en JSON + respuesta con el LLM local (Ollama), con comprobaciones
generar *ARGS:
    python -m caso_uso_llm.generate.run {{ARGS}}

# Fase 6 (adelantada): valida el juez (canaries, controles, gold) y evalúa las respuestas de la Fase 4
juez:
    python -m caso_uso_llm.evals.run_judge

# Calibración del juez: kappa por criterio cuando se rellenan las columnas humano_* del CSV
calibrar:
    python -m caso_uso_llm.evals.calibrate

# Fase 5: recuperación de políticas y respuestas aprobadas (BM25, bge-m3 e híbrida), con recall@k y MRR
rag:
    python -m caso_uso_llm.rag.eval_retrieval

# Fase 5: respuestas con contexto recuperado (prompt v5) frente a v4 sin contexto
rag-generar *ARGS:
    python -m caso_uso_llm.rag.generate_rag {{ARGS}}

# Comprueba que Ollama tiene el modelo entero en la GPU (falla si se ha ido a la CPU)
gpu-ollama *ARGS:
    python -m caso_uso_llm.ollama_gpu {{ARGS}}

# Fase 5: juez con ficha (rúbrica v2f) sobre v4, v5 y v6, con puerta de canaries y pares
rag-juez:
    python -m caso_uso_llm.rag.judge_rag

# Fase 5: pipeline completo (clasificador CPU + RAG + generador + guardarraíles + juez) y cola de revisión
pipeline *ARGS:
    python -m caso_uso_llm.pipeline {{ARGS}}

# Demo en Gradio: responder una reseña y revisar la cola humana (http://127.0.0.1:7860)
app:
    python -m caso_uso_llm.app

# ¿Generador pequeño para la demo? Compara un modelo menor con el 27B (mismo prompt, RAG y juez)
modelo-pequeno *ARGS:
    python -m caso_uso_llm.rag.small_model {{ARGS}}

# Fase 9: latencia por etapa del uso interactivo (sin caché; carga frente a inferencia)
#   -> results/latencia_*.jsonl + reports/phase9_latencia.md. Ej.: just latencia --reps 3
latencia *ARGS:
    python -m caso_uso_llm.latency {{ARGS}}

# Demo en modo repetición: reconstruye casos.json y la abre (sin modelos; http://127.0.0.1:7861)
replay:
    python scripts/build_replay.py
    python demo_replay/app.py

# Demo en vivo con contraseña (DEMO_USER y DEMO_PASS en el entorno). Publicarla con un túnel:
#   cloudflared tunnel --url http://127.0.0.1:7860     (Defender bloquea el túnel de Gradio)
app-live:
    python -m caso_uso_llm.app --auth

# Demo en modo recogida: solo el formulario, sin modelos; guarda en data/live/resenas_recogidas.jsonl
# (sin contraseña; --auth la pide con DEMO_USER y DEMO_PASS). Se publica con el mismo túnel que app-live
recoger:
    python -m caso_uso_llm.recoger
