from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def load_env_file(env_path: str = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned_value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), cleaned_value)

    if "LANGFUSE_HOST" not in os.environ and "LANGFUSE_BASE_URL" in os.environ:
        os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]


load_env_file()

from simulation import DungeonSimulation


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def ensure_replay_server(port: int = 8123) -> str | None:
    if _port_is_open(port):
        return f"http://127.0.0.1:{port}"

    dist_path = Path("frontend/dist/index.html")
    if not dist_path.exists():
        return None

    subprocess.Popen(
        [sys.executable, "replay_server.py", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(20):
        if _port_is_open(port):
            return f"http://127.0.0.1:{port}"
        time.sleep(0.15)
    return None


def main() -> None:
    output_dir = Path("artifacts")
    trace_path = output_dir / "latest_trace.json"

    simulation = DungeonSimulation(seed=7, max_steps=80)
    result = simulation.run(str(trace_path))

    latest_logs = simulation.logger.history[-2:] if simulation.logger.history else []
    tracer_status = simulation.tracer.status()
    replay_url = ensure_replay_server()
    if replay_url:
        webbrowser.open(replay_url)
    print(simulation.render(result.summary["steps"], latest_logs))
    print("")
    print(result.analysis_report)
    print("")
    print(f"Langfuse enabled: {tracer_status['langfuse_enabled']}")
    print(f"Langfuse status: {tracer_status['init_status']}")
    print(f"Python executable: {tracer_status['python_executable']}")
    print(f"Langfuse trace id: {tracer_status['trace_id']}")
    if tracer_status["trace_url"]:
        print(f"Langfuse trace url: {tracer_status['trace_url']}")
    if replay_url:
        print(f"Replay UI: {replay_url}")
    else:
        print("Replay UI: unavailable (build frontend with `npm install` then `npm run build`)")
    print(f"Trace written to: {result.trace_path}")


if __name__ == "__main__":
    main()
