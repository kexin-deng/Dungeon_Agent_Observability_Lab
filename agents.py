from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DIRECTION_VECTORS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


@dataclass
class AgentAction:
    tool: str
    args: dict[str, Any]
    thought: str


@dataclass
class AgentState:
    agent_id: str
    position: tuple[int, int]
    inventory: list[str] = field(default_factory=list)
    inbox: list[dict[str, Any]] = field(default_factory=list)
    outbox: list[dict[str, Any]] = field(default_factory=list)
    belief: dict[str, Any] = field(
        default_factory=lambda: {
            "key_position": None,
            "door_position": None,
            "exit_position": None,
            "door_unlocked": False,
            "walls": [],
            "has_key": False,
            "teammate_last_position": None,
            "visited_positions": [],
            "visit_counts": {},
        }
    )
    recent_actions: list[str] = field(default_factory=list)

    def remember_position(self, position: tuple[int, int]) -> None:
        visited = self.belief.setdefault("visited_positions", [])
        if position not in visited:
            visited.append(position)
        visit_counts = self.belief.setdefault("visit_counts", {})
        key = f"{position[0]},{position[1]}"
        visit_counts[key] = visit_counts.get(key, 0) + 1

    def note_action(self, action_name: str) -> None:
        self.recent_actions.append(action_name)
        if len(self.recent_actions) > 6:
            self.recent_actions.pop(0)


class DungeonAgent:
    """A simple, intentionally imperfect agent focused on traceability."""

    def __init__(self, state: AgentState, teammate_id: str) -> None:
        self.state = state
        self.teammate_id = teammate_id

    def observe(self, observation: dict[str, Any]) -> None:
        visible_cells = observation["visible_cells"]
        self.state.remember_position(self.state.position)
        self.state.belief["has_key"] = "key" in self.state.inventory
        self.state.belief["door_unlocked"] = observation["door_unlocked"]
        if self.state.belief["has_key"]:
            self.state.belief["key_position"] = None
        for cell in visible_cells:
            position = tuple(cell["position"])
            cell_type = cell["cell_type"]
            if cell_type == "key":
                self.state.belief["key_position"] = position
            elif cell_type == "door":
                self.state.belief["door_position"] = position
                self.state.belief["door_unlocked"] = cell.get("door_unlocked", False)
            elif cell_type == "exit":
                self.state.belief["exit_position"] = position
            elif cell_type == "wall":
                walls = self.state.belief.setdefault("walls", [])
                if position not in walls:
                    walls.append(position)
        if self.state.inbox:
            self._process_messages()

    def choose_action(self, observation: dict[str, Any]) -> AgentAction:
        current_position = tuple(observation["self_position"])
        self.state.remember_position(current_position)

        for cell in observation["visible_cells"]:
            if tuple(cell["position"]) == current_position and cell["cell_type"] == "key":
                return AgentAction(
                    tool="pick_up",
                    args={"item": "key"},
                    thought="I am standing on the key, so I should pick it up.",
                )

        for cell in observation["visible_cells"]:
            if cell["cell_type"] == "door":
                if "key" in self.state.inventory and not cell.get("door_unlocked", False):
                    return AgentAction(
                        tool="use_item",
                        args={"item": "key", "target": "door"},
                        thought="The locked door is nearby and I have the key, so I should unlock it.",
                    )

        if self._should_send_message():
            message = self._compose_message()
            if message:
                return AgentAction(
                    tool="send_message",
                    args={"agent": self.teammate_id, "message": message},
                    thought="I learned something useful and should share it with my teammate.",
                )

        unseen_priority = self._preferred_direction(observation)
        if unseen_priority:
            return AgentAction(
                tool="move",
                args={"direction": unseen_priority},
                thought=f"I will explore by moving {unseen_priority}.",
            )

        return AgentAction(
            tool="look",
            args={},
            thought="I am uncertain about the next move, so I will refresh my local observation.",
        )

    def _process_messages(self) -> None:
        for message in self.state.inbox:
            kind = message.get("kind")
            if kind == "location_update":
                item = message.get("item")
                position = tuple(message["position"])
                if item == "key":
                    self.state.belief["key_position"] = position
                elif item == "door":
                    self.state.belief["door_position"] = position
                elif item == "exit":
                    self.state.belief["exit_position"] = position
            elif kind == "status_update":
                self.state.belief["teammate_last_position"] = tuple(message["position"])
                self.state.belief["teammate_has_key"] = message.get("has_key", False)
                self.state.belief["door_unlocked"] = message.get(
                    "door_unlocked",
                    self.state.belief["door_unlocked"],
                )
                known_locations = message.get("known_locations", {})
                for item, position in known_locations.items():
                    if position is None:
                        continue
                    self.state.belief[f"{item}_position"] = tuple(position)
        self.state.inbox.clear()

    def _should_send_message(self) -> bool:
        if not self.state.recent_actions:
            return True
        recent = self.state.recent_actions[-2:]
        return all(action != "send_message" for action in recent)

    def _compose_message(self) -> dict[str, Any] | None:
        for item_name, belief_key in [
            ("door", "door_position"),
            ("exit", "exit_position"),
            ("key", "key_position"),
        ]:
            if self.state.belief.get(belief_key) is not None:
                return {
                    "kind": "location_update",
                    "item": item_name,
                    "position": list(self.state.belief[belief_key]),
                }
        return {
            "kind": "status_update",
            "position": list(self.state.position),
            "has_key": self.state.belief["has_key"],
            "door_unlocked": self.state.belief["door_unlocked"],
            "known_locations": {
                "key": list(self.state.belief["key_position"]) if self.state.belief["key_position"] else None,
                "door": list(self.state.belief["door_position"]) if self.state.belief["door_position"] else None,
                "exit": list(self.state.belief["exit_position"]) if self.state.belief["exit_position"] else None,
            },
        }

    def _preferred_direction(self, observation: dict[str, Any]) -> str | None:
        walkable_neighbors = {
            cell["direction"]: cell
            for cell in observation["visible_cells"]
            if cell["direction"] in DIRECTION_VECTORS and cell["is_walkable"]
        }

        target = self._choose_target()
        if target:
            best_direction = self._move_toward_target(target, walkable_neighbors)
            if best_direction:
                return best_direction

        for direction, cell in walkable_neighbors.items():
            position = tuple(cell["position"])
            if position not in self.state.belief["visited_positions"]:
                return direction

        if not walkable_neighbors:
            return None

        visit_counts = self.state.belief.get("visit_counts", {})
        return min(
            walkable_neighbors,
            key=lambda direction: visit_counts.get(
                f"{walkable_neighbors[direction]['position'][0]},{walkable_neighbors[direction]['position'][1]}",
                0,
            ),
        )

    def _choose_target(self) -> tuple[int, int] | None:
        if (
            "key" not in self.state.inventory
            and not self.state.belief["door_unlocked"]
            and self.state.belief["key_position"]
        ):
            return tuple(self.state.belief["key_position"])
        if "key" in self.state.inventory and self.state.belief["door_position"]:
            return tuple(self.state.belief["door_position"])
        if self.state.belief["exit_position"] and self.state.belief["door_unlocked"]:
            return tuple(self.state.belief["exit_position"])
        if self.state.belief["exit_position"] and self.state.belief.get("door_position") is not None:
            return tuple(self.state.belief["exit_position"])
        return None

    def _move_toward_target(
        self,
        target: tuple[int, int],
        walkable_neighbors: dict[str, dict[str, Any]],
    ) -> str | None:
        current_row, current_col = self.state.position
        best_choice = None
        best_distance = None
        best_visits = None
        visit_counts = self.state.belief.get("visit_counts", {})

        for direction, cell in walkable_neighbors.items():
            next_row, next_col = cell["position"]
            distance = abs(target[0] - next_row) + abs(target[1] - next_col)
            visit_key = f"{next_row},{next_col}"
            visits = visit_counts.get(visit_key, 0)
            if (
                best_distance is None
                or distance < best_distance
                or (distance == best_distance and (best_visits is None or visits < best_visits))
            ):
                best_distance = distance
                best_visits = visits
                best_choice = direction

        if best_choice is None and target == (current_row, current_col):
            return None
        return best_choice
