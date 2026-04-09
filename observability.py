from __future__ import annotations

import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any


def _safe_dict(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload if payload is not None else {}


def _langfuse_trace_id(seed: str | None = None) -> str:
    if seed:
        filtered = "".join(char for char in seed.lower() if char in "0123456789abcdef")
        if len(filtered) >= 32:
            return filtered[:32]
    return uuid.uuid4().hex


@dataclass
class StepTraceHandle:
    tracer: "LangfuseTracer"
    step: int
    agent_id: str
    observation: dict[str, Any]
    trace_id: str
    step_name: str
    step_client: Any = None
    enabled: bool = False

    def log_reasoning(
        self,
        llm_input: dict[str, Any],
        llm_output: dict[str, Any],
        latency_ms: float,
    ) -> None:
        self.tracer._record_span(
            parent=self.step_client,
            observation_type="generation",
            name=f"{self.step_name}.reasoning",
            input_payload=llm_input,
            output_payload=llm_output,
            metadata={"latency_ms": latency_ms, "component": "llm_or_reasoning"},
            enabled=self.enabled,
        )

    def log_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any],
        latency_ms: float,
    ) -> None:
        self.tracer._record_span(
            parent=self.step_client,
            observation_type="tool",
            name=f"{self.step_name}.tool.{tool_name}",
            input_payload=tool_input,
            output_payload=tool_output,
            metadata={"latency_ms": latency_ms, "component": "tool"},
            enabled=self.enabled,
        )

    def end(
        self,
        output_payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        if not self.enabled or self.step_client is None:
            return
        try:
            if hasattr(self.step_client, "update"):
                self.step_client.update(output=output_payload, metadata=metadata)
            if hasattr(self.step_client, "end"):
                self.step_client.end()
        except Exception:
            return


class LangfuseTracer:
    """Optional Langfuse integration with a local no-op fallback."""

    def __init__(self) -> None:
        self.enabled = False
        self.client = None
        self.root_observation = None
        self.root_trace_id: str | None = None
        self.flush_delay_seconds = float(os.getenv("LANGFUSE_FLUSH_DELAY_SECONDS", "2"))
        self._bootstrap()

    def _bootstrap(self) -> None:
        self.init_status = "Langfuse not initialized."
        try:
            from langfuse import Langfuse  # type: ignore
        except Exception as exc:
            self.init_status = f"Langfuse init failed: {exc}"
            return

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST")

        if not (public_key and secret_key):
            self.init_status = "Langfuse keys missing."
            return

        try:
            self.client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            self.enabled = True
            self.init_status = "Langfuse enabled."
        except Exception as exc:
            self.client = None
            self.enabled = False
            self.init_status = f"Langfuse init failed: {exc}"

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        self.root_trace_id = _langfuse_trace_id(run_id)
        if not self.enabled or self.client is None:
            return
        try:
            if hasattr(self.client, "start_observation"):
                self.root_observation = self.client.start_observation(
                    trace_context={"trace_id": self.root_trace_id},
                    name="dungeon-agent-simulation",
                    as_type="chain",
                    input={"run_id": run_id},
                    metadata=metadata,
                )
        except Exception as exc:
            self.root_observation = None
            self.enabled = False
            self.init_status = f"Langfuse start_run failed: {exc}"

    def start_step(
        self,
        step: int,
        agent_id: str,
        observation: dict[str, Any],
    ) -> StepTraceHandle:
        trace_id = f"{self.root_trace_id or uuid.uuid4().hex}-step-{step}-{agent_id}"
        step_name = f"step-{step}-agent-{agent_id}"
        step_client = None

        if self.enabled and self.root_observation is not None:
            try:
                if hasattr(self.root_observation, "start_observation"):
                    step_client = self.root_observation.start_observation(
                        name=step_name,
                        as_type="agent",
                        input=observation,
                        metadata={"step": step, "agent_id": agent_id},
                    )
            except Exception:
                step_client = None

        return StepTraceHandle(
            tracer=self,
            step=step,
            agent_id=agent_id,
            observation=observation,
            trace_id=trace_id,
            step_name=step_name,
            step_client=step_client,
            enabled=self.enabled and step_client is not None,
        )

    def finish_run(self, summary: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            if self.root_observation is not None and hasattr(self.root_observation, "update"):
                self.root_observation.update(output=summary)
            if self.root_observation is not None and hasattr(self.root_observation, "end"):
                self.root_observation.end()
            if self.client is not None and hasattr(self.client, "flush"):
                self.client.flush()
            if self.flush_delay_seconds > 0:
                time.sleep(self.flush_delay_seconds)
            if self.client is not None and hasattr(self.client, "shutdown"):
                self.client.shutdown()
        except Exception:
            return

    def status(self) -> dict[str, Any]:
        trace_url = None
        if self.client is not None and self.root_trace_id and hasattr(self.client, "get_trace_url"):
            try:
                trace_url = self.client.get_trace_url(trace_id=self.root_trace_id)
            except Exception:
                trace_url = None
        return {
            "langfuse_enabled": self.enabled,
            "has_credentials": bool(
                os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
            ),
            "init_status": self.init_status,
            "python_executable": sys.executable,
            "flush_delay_seconds": self.flush_delay_seconds,
            "trace_id": self.root_trace_id,
            "trace_url": trace_url,
        }

    def _record_span(
        self,
        parent: Any,
        observation_type: str,
        name: str,
        input_payload: dict[str, Any] | None,
        output_payload: dict[str, Any] | None,
        metadata: dict[str, Any] | None,
        enabled: bool,
    ) -> None:
        if not enabled or parent is None:
            return
        try:
            if hasattr(parent, "start_observation"):
                child = parent.start_observation(
                    name=name,
                    as_type=observation_type,
                    input=_safe_dict(input_payload),
                    metadata=_safe_dict(metadata),
                )
                if hasattr(child, "update"):
                    child.update(output=_safe_dict(output_payload), metadata=_safe_dict(metadata))
                if hasattr(child, "end"):
                    child.end()
        except Exception:
            return
