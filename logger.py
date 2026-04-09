from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepLog:
    step: int
    agent_id: str
    observation: dict[str, Any]
    thought: str | None
    llm_input: dict[str, Any] | None
    llm_output: dict[str, Any] | None
    action: str
    tool_input: dict[str, Any]
    tool_output: dict[str, Any]
    result_state: dict[str, Any]
    belief_state: dict[str, Any]
    ground_truth: dict[str, Any]
    environment_state: dict[str, Any]
    delivered_messages: list[dict[str, Any]]
    anomaly: dict[str, Any] | None = None
    latency_breakdown_ms: dict[str, float | None] | None = None
    langfuse_trace: dict[str, Any] | None = None
    latency_ms: float | None = None


@dataclass
class SimulationLogger:
    run_id: str
    history: list[StepLog] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def log_step(self, entry: StepLog) -> None:
        self.history.append(entry)

    def log_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def export_json(self, path: str | Path, summary: dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "summary": summary,
            "events": self.events,
            "steps": [self._serialize_step(step) for step in self.history],
        }
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _serialize_step(self, step: StepLog) -> dict[str, Any]:
        return {
            "step": step.step,
            "agent_id": step.agent_id,
            "observation": step.observation,
            "thought": step.thought,
            "llm_input": step.llm_input,
            "llm_output": step.llm_output,
            "action": step.action,
            "tool_input": step.tool_input,
            "tool_output": step.tool_output,
            "result_state": step.result_state,
            "belief_state": step.belief_state,
            "ground_truth": step.ground_truth,
            "environment_state": step.environment_state,
            "delivered_messages": step.delivered_messages,
            "anomaly": step.anomaly,
            "latency_breakdown_ms": step.latency_breakdown_ms,
            "langfuse_trace": step.langfuse_trace,
            "latency_ms": step.latency_ms,
        }


def build_analysis_report(history: list[StepLog], summary: dict[str, Any]) -> str:
    lines = [
        f"Run status: {summary['status']}",
        f"Total turns: {summary['steps']}",
        "What happened:",
    ]

    for event in summary.get("major_events", []):
        lines.append(f"- step {event['step']}: {event['description']}")

    lines.append("Why it happened:")
    repeated = _detect_repeated_actions(history)
    if repeated:
        for item in repeated:
            lines.append(f"- {item}")
    else:
        lines.append("- No severe action loops detected.")

    loop_findings = _detect_loop_anomalies(history)
    for item in loop_findings:
        lines.append(f"- {item}")

    divergence = _detect_belief_divergence(history)
    if divergence:
        lines.append("What should change:")
        for item in divergence:
            lines.append(f"- {item}")
    else:
        lines.append("What should change:")
        lines.append("- Beliefs stayed close to reality; focus next on richer coordination strategies.")

    return "\n".join(lines)


def _detect_repeated_actions(history: list[StepLog]) -> list[str]:
    findings: list[str] = []
    by_agent: dict[str, list[str]] = {}
    for step in history:
        by_agent.setdefault(step.agent_id, []).append(step.action)

    for agent_id, actions in by_agent.items():
        for index in range(len(actions) - 2):
            window = actions[index : index + 3]
            if len(set(window)) == 1:
                findings.append(
                    f"Agent {agent_id} repeated `{window[0]}` three turns in a row near step {index + 1}."
                )
                break
    return findings


def _detect_belief_divergence(history: list[StepLog]) -> list[str]:
    findings: list[str] = []
    for step in history:
        belief = step.belief_state
        truth = step.ground_truth
        if belief.get("key_position") and truth.get("key_position"):
            if tuple(belief["key_position"]) != tuple(truth["key_position"]):
                findings.append(
                    f"Agent {step.agent_id} believed the key was at {belief['key_position']} during step {step.step},"
                    f" but reality was {truth['key_position']}."
                )
                break
        if belief.get("door_position") and tuple(belief["door_position"]) != tuple(truth["door_position"]):
            findings.append(
                f"Agent {step.agent_id} believed the door was at {belief['door_position']} during step {step.step},"
                f" but reality was {truth['door_position']}."
            )
            break
    return findings


def _detect_loop_anomalies(history: list[StepLog]) -> list[str]:
    findings: list[str] = []
    seen_agents: set[str] = set()
    for step in history:
        anomaly = step.anomaly
        if not anomaly or anomaly.get("type") != "loop" or step.agent_id in seen_agents:
            continue
        seen_agents.add(step.agent_id)
        findings.append(
            f"Agent {step.agent_id} revisited {anomaly['position']} {anomaly['count']} times by step {step.step}."
        )
    return findings
