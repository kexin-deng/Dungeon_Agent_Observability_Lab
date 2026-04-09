from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass
from typing import Any

from agents import AgentState, DungeonAgent
from logger import SimulationLogger, StepLog
from observability import LangfuseTracer
import tools


GRID_SIZE = 8
AGENT_IDS = ("A", "B")


@dataclass
class RunResult:
    summary: dict[str, Any]
    analysis_report: str
    trace_path: str


class DungeonSimulation:
    def __init__(self, seed: int = 7, max_steps: int = 80) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.max_steps = max_steps
        self.turn_index = 0
        self.message_queue: list[dict[str, Any]] = []

        self.walls: set[tuple[int, int]] = set()
        self.key_position = (0, 0)
        self.door_position = (0, 0)
        self.exit_position = (0, 0)
        self.key_picked = False
        self.door_unlocked = False

        self.agent_states: dict[str, AgentState] = {}
        self.agents: dict[str, DungeonAgent] = {}
        self.recorded_exit_arrivals: set[str] = set()

        self.logger = SimulationLogger(run_id=f"run-{uuid.uuid4().hex[:8]}")
        self.tracer = LangfuseTracer()
        self._initialize_valid_layout()

    def _initialize_valid_layout(self) -> None:
        while True:
            self.walls = set()
            self.agent_states = {}
            self.agents = {}
            self._build_world()
            self._build_agents()
            if self._layout_is_valid():
                return

    def _build_world(self) -> None:
        blocked = set()
        self.key_position = self._random_open_cell(blocked)
        blocked.add(self.key_position)
        self.door_position = self._random_open_cell(blocked)
        blocked.add(self.door_position)
        self.exit_position = self._random_open_cell(blocked)
        blocked.add(self.exit_position)

        wall_count = self.rng.randint(5, 8)
        while len(self.walls) < wall_count:
            candidate = self._random_open_cell(blocked | self.walls)
            self.walls.add(candidate)

    def _build_agents(self) -> None:
        occupied = {self.key_position, self.door_position, self.exit_position, *self.walls}
        for agent_id in AGENT_IDS:
            position = self._random_open_cell(occupied)
            occupied.add(position)
            state = AgentState(agent_id=agent_id, position=position)
            self.agent_states[agent_id] = state

        self.agents["A"] = DungeonAgent(self.agent_states["A"], teammate_id="B")
        self.agents["B"] = DungeonAgent(self.agent_states["B"], teammate_id="A")

    def _layout_is_valid(self) -> bool:
        positions = [state.position for state in self.agent_states.values()]
        if not positions:
            return False

        key_reachable = any(self._path_exists(start, self.key_position, False) for start in positions)
        door_reachable = self._path_exists(self.key_position, self.door_position, False)
        exit_reachable = self._path_exists(self.door_position, self.exit_position, True)
        agents_can_finish = all(
            self._path_exists(start, self.exit_position, True, allow_locked_door=True)
            for start in positions
        )
        return key_reachable and door_reachable and exit_reachable and agents_can_finish

    def _random_open_cell(self, blocked: set[tuple[int, int]]) -> tuple[int, int]:
        while True:
            candidate = (self.rng.randrange(GRID_SIZE), self.rng.randrange(GRID_SIZE))
            if candidate not in blocked:
                return candidate

    def in_bounds(self, position: tuple[int, int]) -> bool:
        row, col = position
        return 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE

    def get_visible_cells(self, agent_id: str) -> list[dict[str, Any]]:
        agent = self.agent_states[agent_id]
        visible = []
        for direction, delta in [("self", (0, 0)), *tools.DIRECTIONS.items()]:
            if direction == "self":
                row_delta, col_delta = delta
            else:
                row_delta, col_delta = delta
            position = (agent.position[0] + row_delta, agent.position[1] + col_delta)
            if not self.in_bounds(position):
                continue
            cell = self.describe_cell(position)
            cell["position"] = list(position)
            cell["direction"] = direction
            cell["is_walkable"] = self.is_walkable(position)
            visible.append(cell)
        return visible

    def describe_cell(self, position: tuple[int, int]) -> dict[str, Any]:
        if position in self.walls:
            return {"cell_type": "wall"}
        if position == self.key_position and not self.key_picked:
            return {"cell_type": "key"}
        if position == self.door_position:
            return {"cell_type": "door", "door_unlocked": self.door_unlocked}
        if position == self.exit_position:
            return {"cell_type": "exit"}
        for agent_id, state in self.agent_states.items():
            if state.position == position:
                return {"cell_type": "agent", "agent_id": agent_id}
        return {"cell_type": "empty"}

    def is_walkable(self, position: tuple[int, int]) -> bool:
        if position in self.walls:
            return False
        if position == self.door_position and not self.door_unlocked:
            return False
        return True

    def _path_exists(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
        door_open: bool,
        allow_locked_door: bool = False,
    ) -> bool:
        frontier = [start]
        visited = {start}

        while frontier:
            position = frontier.pop(0)
            if position == goal:
                return True
            for row_delta, col_delta in tools.DIRECTIONS.values():
                next_position = (position[0] + row_delta, position[1] + col_delta)
                if not self.in_bounds(next_position) or next_position in visited or next_position in self.walls:
                    continue
                if (
                    next_position == self.door_position
                    and next_position != goal
                    and not door_open
                    and not allow_locked_door
                ):
                    continue
                visited.add(next_position)
                frontier.append(next_position)
        return False

    def build_observation(self, agent_id: str) -> dict[str, Any]:
        state = self.agent_states[agent_id]
        delivered = self._deliver_messages(agent_id)
        visible_cells = self.get_visible_cells(agent_id)
        observation = {
            "self_position": list(state.position),
            "inventory": list(state.inventory),
            "visible_cells": visible_cells,
            "received_messages": delivered,
            "door_unlocked": self.door_unlocked,
            "door_position": list(self.door_position),
        }
        self.agents[agent_id].observe(observation)
        return observation

    def _deliver_messages(self, agent_id: str) -> list[dict[str, Any]]:
        delivered: list[dict[str, Any]] = []
        remaining: list[dict[str, Any]] = []
        for message in self.message_queue:
            if message["to"] == agent_id and message["deliver_on_turn"] <= self.turn_index:
                payload = {
                    "from": message["from"],
                    **message["message"],
                }
                self.agent_states[agent_id].inbox.append(payload)
                delivered.append(payload)
            else:
                remaining.append(message)
        self.message_queue = remaining
        return delivered

    def run(self, trace_path: str) -> RunResult:
        major_events: list[dict[str, Any]] = []
        self.tracer.start_run(
            self.logger.run_id,
            metadata={
                "seed": self.seed,
                "max_steps": self.max_steps,
                "grid_size": GRID_SIZE,
                "langfuse_enabled": self.tracer.status()["langfuse_enabled"],
            },
        )

        for step in range(1, self.max_steps + 1):
            self.turn_index = step
            for agent_id in AGENT_IDS:
                observation = self.build_observation(agent_id)
                step_trace = self.tracer.start_step(step, agent_id, observation)

                decision_start = time.perf_counter()
                action = self.agents[agent_id].choose_action(observation)
                reasoning_latency_ms = round((time.perf_counter() - decision_start) * 1000, 3)
                llm_input = {
                    "observation": observation,
                    "belief_before_action": dict(self.agent_states[agent_id].belief),
                }
                llm_output = {
                    "thought": action.thought,
                    "tool": action.tool,
                    "args": action.args,
                }
                step_trace.log_reasoning(llm_input, llm_output, reasoning_latency_ms)

                step_start = time.perf_counter()
                tool_start = time.perf_counter()
                tool_output = self.execute_action(agent_id, action.tool, action.args)
                tool_latency_ms = round((time.perf_counter() - tool_start) * 1000, 3)
                self.agent_states[agent_id].note_action(action.tool)
                self._sync_belief_after_action(agent_id)
                step_latency_ms = round((time.perf_counter() - step_start) * 1000, 3)

                result_state = self.snapshot_agent_state(agent_id)
                ground_truth = self.snapshot_ground_truth()
                environment_state = self.snapshot_environment_state()
                anomaly = self._detect_anomaly(agent_id)
                latency_breakdown = {
                    "step_ms": step_latency_ms,
                    "tool_ms": tool_latency_ms,
                    "llm_ms": reasoning_latency_ms,
                }
                step_trace.log_tool(action.tool, action.args, tool_output, tool_latency_ms)
                step_trace.end(
                    output_payload={
                        "tool_output": tool_output,
                        "environment_state": environment_state,
                        "anomaly": anomaly,
                    },
                    metadata={
                        "latency_breakdown_ms": latency_breakdown,
                        "belief_state": dict(self.agent_states[agent_id].belief),
                    },
                )

                self.logger.log_step(
                    StepLog(
                        step=step,
                        agent_id=agent_id,
                        observation=observation,
                        thought=action.thought,
                        llm_input=llm_input,
                        llm_output=llm_output,
                        action=action.tool,
                        tool_input=action.args,
                        tool_output=tool_output,
                        result_state=result_state,
                        belief_state=dict(self.agent_states[agent_id].belief),
                        ground_truth=ground_truth,
                        environment_state=environment_state,
                        delivered_messages=observation["received_messages"],
                        anomaly=anomaly,
                        latency_breakdown_ms=latency_breakdown,
                        langfuse_trace={
                            "trace_id": step_trace.trace_id,
                            "step_name": step_trace.step_name,
                            "enabled": step_trace.enabled,
                        },
                        latency_ms=step_latency_ms,
                    )
                )

                event = self._capture_major_event(step, agent_id, action.tool, tool_output)
                if event:
                    major_events.append(event)
                    self.logger.log_event(event)

                if self.is_success():
                    summary = self._build_summary(step, "success", major_events)
                    self.tracer.finish_run(summary)
                    self.logger.export_json(trace_path, summary)
                    from logger import build_analysis_report

                    return RunResult(
                        summary=summary,
                        analysis_report=build_analysis_report(self.logger.history, summary),
                        trace_path=trace_path,
                    )

            if self._agents_stuck():
                summary = self._build_summary(step, "agents_stuck", major_events)
                self.tracer.finish_run(summary)
                self.logger.export_json(trace_path, summary)
                from logger import build_analysis_report

                return RunResult(
                    summary=summary,
                    analysis_report=build_analysis_report(self.logger.history, summary),
                    trace_path=trace_path,
                )

        summary = self._build_summary(self.max_steps, "max_steps_reached", major_events)
        self.tracer.finish_run(summary)
        self.logger.export_json(trace_path, summary)
        from logger import build_analysis_report

        return RunResult(
            summary=summary,
            analysis_report=build_analysis_report(self.logger.history, summary),
            trace_path=trace_path,
        )

    def execute_action(self, agent_id: str, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        dispatch = {
            "move": lambda: tools.move(self, agent_id, args["direction"]),
            "look": lambda: tools.look(self, agent_id),
            "pick_up": lambda: tools.pick_up(self, agent_id, args["item"]),
            "check_inventory": lambda: tools.check_inventory(self, agent_id),
            "use_item": lambda: tools.use_item(self, agent_id, args["item"], args["target"]),
            "send_message": lambda: tools.send_message(self, agent_id, args["agent"], args["message"]),
        }
        return dispatch[tool_name]()

    def is_success(self) -> bool:
        return self.door_unlocked and all(
            state.position == self.exit_position for state in self.agent_states.values()
        )

    def _agents_stuck(self) -> bool:
        return all(
            len(state.recent_actions) >= 4 and len(set(state.recent_actions[-4:])) == 1
            for state in self.agent_states.values()
        )

    def snapshot_agent_state(self, agent_id: str) -> dict[str, Any]:
        state = self.agent_states[agent_id]
        return {
            "position": list(state.position),
            "inventory": list(state.inventory),
            "inbox_size": len(state.inbox),
            "door_unlocked": self.door_unlocked,
        }

    def snapshot_ground_truth(self) -> dict[str, Any]:
        return {
            "key_position": list(self.key_position) if not self.key_picked else None,
            "key_picked": self.key_picked,
            "door_position": list(self.door_position),
            "door_unlocked": self.door_unlocked,
            "exit_position": list(self.exit_position),
            "agent_positions": {
                agent_id: list(state.position) for agent_id, state in self.agent_states.items()
            },
        }

    def snapshot_environment_state(self) -> dict[str, Any]:
        return {
            "door_position": list(self.door_position),
            "door_unlocked": self.door_unlocked,
            "exit_position": list(self.exit_position),
            "key_position": list(self.key_position) if not self.key_picked else None,
            "message_queue_depth": len(self.message_queue),
        }

    def _capture_major_event(
        self,
        step: int,
        agent_id: str,
        action_name: str,
        tool_output: dict[str, Any],
    ) -> dict[str, Any] | None:
        if tool_output.get("inventory") and "key" in tool_output["inventory"]:
            return {"step": step, "description": f"Agent {agent_id} picked up the key."}
        if action_name == "use_item" and tool_output.get("door_unlocked"):
            return {"step": step, "description": f"Agent {agent_id} unlocked the door."}
        if (
            self.agent_states[agent_id].position == self.exit_position
            and agent_id not in self.recorded_exit_arrivals
        ):
            self.recorded_exit_arrivals.add(agent_id)
            return {"step": step, "description": f"Agent {agent_id} reached the exit."}
        return None

    def _build_summary(
        self,
        step_count: int,
        status: str,
        major_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "status": status,
            "steps": step_count,
            "seed": self.seed,
            "door_unlocked": self.door_unlocked,
            "observability": self.tracer.status(),
            "agents_at_exit": {
                agent_id: state.position == self.exit_position
                for agent_id, state in self.agent_states.items()
            },
            "major_events": major_events,
            "loop_anomalies": self._collect_summary_anomalies(),
        }

    def _sync_belief_after_action(self, agent_id: str) -> None:
        state = self.agent_states[agent_id]
        state.belief["has_key"] = "key" in state.inventory
        state.belief["door_unlocked"] = self.door_unlocked
        if state.belief["has_key"]:
            state.belief["key_position"] = None
        if self.door_unlocked and state.belief.get("door_position") is None:
            state.belief["door_position"] = self.door_position

    def _detect_anomaly(self, agent_id: str, loop_threshold: int = 10) -> dict[str, Any] | None:
        state = self.agent_states[agent_id]
        position_key = f"{state.position[0]},{state.position[1]}"
        visit_count = state.belief.get("visit_counts", {}).get(position_key, 0)
        if visit_count > loop_threshold:
            return {
                "type": "loop",
                "position": [state.position[0], state.position[1]],
                "count": visit_count,
                "threshold": loop_threshold,
            }
        return None

    def _collect_summary_anomalies(self, loop_threshold: int = 10) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        for agent_id, state in self.agent_states.items():
            for position_key, visit_count in state.belief.get("visit_counts", {}).items():
                if visit_count <= loop_threshold:
                    continue
                row_text, col_text = position_key.split(",")
                anomalies.append(
                    {
                        "agent_id": agent_id,
                        "type": "loop",
                        "position": [int(row_text), int(col_text)],
                        "count": visit_count,
                        "threshold": loop_threshold,
                    }
                )
        return anomalies

    def render(self, step: int, latest_logs: list[StepLog]) -> str:
        grid = []
        for row in range(GRID_SIZE):
            cells = []
            for col in range(GRID_SIZE):
                position = (row, col)
                symbol = "."
                if position in self.walls:
                    symbol = "#"
                elif position == self.key_position and not self.key_picked:
                    symbol = "K"
                elif position == self.door_position:
                    symbol = "D" if not self.door_unlocked else "d"
                elif position == self.exit_position:
                    symbol = "E"

                for agent_id, state in self.agent_states.items():
                    if state.position == position:
                        symbol = agent_id
                cells.append(symbol)
            grid.append(" ".join(cells))

        panel_lines = [f"Step {step}", "Grid:"]
        panel_lines.extend(grid)
        panel_lines.append("")
        panel_lines.append("Logs:")
        for log in latest_logs:
            panel_lines.append(
                f"{log.agent_id} | action={log.action} | result={log.tool_output.get('reason', 'ok')}"
            )
            panel_lines.append(f"obs={log.observation['visible_cells']}")
            panel_lines.append(f"belief={log.belief_state}")
            message = log.delivered_messages if log.delivered_messages else "-"
            panel_lines.append(f"message={message}")
            panel_lines.append("")
        return "\n".join(panel_lines)
