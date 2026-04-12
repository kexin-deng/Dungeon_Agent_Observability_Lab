from __future__ import annotations

import argparse
import http.server
import socketserver
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "frontend" / "dist"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


class ReplayRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        normalized = path.split("?", 1)[0].split("#", 1)[0]
        if normalized in {"/", ""}:
            return str(DIST_DIR / "index.html")
        if normalized.startswith("/artifacts/"):
            return str(ARTIFACTS_DIR / normalized.removeprefix("/artifacts/"))
        return str(DIST_DIR / normalized.lstrip("/"))

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8123)
    args = parser.parse_args()

    if not DIST_DIR.exists():
        raise SystemExit("frontend/dist is missing. Run `npm install` and `npm run build` first.")

    with socketserver.TCPServer(("127.0.0.1", args.port), ReplayRequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
