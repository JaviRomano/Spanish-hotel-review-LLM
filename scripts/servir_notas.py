"""Sirve una hoja de notas (scripts/notas_vivo.py) para valorar desde el móvil por el túnel.

Solo expone esa hoja, con contraseña (DEMO_USER y DEMO_PASS en el entorno, como la demo). Las
notas se guardan en el PC mientras se valora (<hoja>.estado.json) y el botón de la hoja escribe
el CSV junto a ella (<hoja>.csv), en data/live/ (fuera de git).

Uso: uv run python scripts/servir_notas.py data/live/notas_vivo_v8_20261026.html
     cloudflared tunnel --url http://127.0.0.1:7870
"""

import argparse
import base64
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 2_000_000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("hoja", type=Path)
    ap.add_argument("--port", type=int, default=7870)
    args = ap.parse_args()
    user, password = os.environ.get("DEMO_USER"), os.environ.get("DEMO_PASS")
    if not (user and password):
        raise SystemExit("Hacen falta DEMO_USER y DEMO_PASS.")
    token = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
    page = args.hoja.resolve()
    state, csv = page.with_suffix(".estado.json"), page.with_suffix(".csv")

    class Handler(BaseHTTPRequestHandler):
        def _auth(self) -> bool:
            if self.headers.get("Authorization") == token:
                return True
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="notas", charset="UTF-8"')
            self.end_headers()
            return False

        def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if not self._auth():
                return
            if self.path in ("/", "/index.html"):
                self._send(page.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/estado":
                body = state.read_bytes() if state.exists() else b"{}"
                self._send(body, "application/json")
            else:
                self._send(b"", "text/plain", 404)

        def do_POST(self) -> None:  # noqa: N802
            if not self._auth():
                return
            n = int(self.headers.get("Content-Length", 0))
            if n > MAX_BODY or self.path not in ("/estado", "/csv"):
                self._send(b"", "text/plain", 400)
                return
            body = self.rfile.read(n)
            if self.path == "/estado":
                json.loads(body)  # solo JSON válido
                state.write_bytes(body)
            else:
                csv.write_bytes(body)
                print(f"CSV guardado: {csv}", flush=True)
            self._send(b"ok", "text/plain")

        def log_message(self, *a) -> None:  # sin ruido por cada guardado
            pass

    print(f"Sirviendo {page.name} en http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
