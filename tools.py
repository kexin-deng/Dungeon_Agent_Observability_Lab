from __future__ import annotations

from typing import Any


DIRECTIONS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


def move(simulation: Any, agent_id: str, direction: str) -> dict[str, Any]:
    agent = simulation.agent_states[agent_id]
    if direction not in DIRECTIONS:
        return {"success": False, "reason": f"Unknown direction `{direction}`."}

    row_delta, col_delta = DIRECTIONS[direction]
    next_position = (agent.position[0] + row_delta, agent.position[1] + col_delta)

    if not simulation.in_bounds(next_position):
        return {"success": False, "reason": "Move blocked by world boundary."}
    if next_position in simulation.walls:
        return {"success": False, "reason": "Move blocked by wall."}
    if next_position == simulation.door_position and not simulation.door_unlocked:
        return {
            "success": False,
            "reason": "Move blocked by locked door.",
            "door_position": list(simulation.door_position),
            "door_unlocked": simulation.door_unlocked,
        }

    agent.position = next_position
    return {
        "success": True,
        "position": list(agent.position),
        "door_unlocked": simulation.door_unlocked,
        "passed_through_door": next_position == simulation.door_position,
    }


def look(simulation: Any, agent_id: str) -> dict[str, Any]:
    return {
        "success": True,
        "visible_cells": simulation.get_visible_cells(agent_id),
    }


def pick_up(simulation: Any, agent_id: str, item: str) -> dict[str, Any]:
    agent = simulation.agent_states[agent_id]
    if item != "key":
        return {"success": False, "reason": f"Item `{item}` cannot be picked up."}
    if simulation.key_picked:
        return {"success": False, "reason": "The key is already gone."}
    if agent.position != simulation.key_position:
        return {"success": False, "reason": "Agent is not standing on the key."}

    simulation.key_picked = True
    agent.inventory.append("key")
    return {"success": True, "inventory": list(agent.inventory)}


def check_inventory(simulation: Any, agent_id: str) -> dict[str, Any]:
    agent = simulation.agent_states[agent_id]
    return {"success": True, "inventory": list(agent.inventory)}


def use_item(simulation: Any, agent_id: str, item: str, target: str) -> dict[str, Any]:
    agent = simulation.agent_states[agent_id]
    if item != "key" or target != "door":
        return {"success": False, "reason": "Only using the key on the door is supported."}
    if "key" not in agent.inventory:
        return {"success": False, "reason": "Agent does not have the key."}
    if _adjacent_or_same(agent.position, simulation.door_position) is False:
        return {"success": False, "reason": "Door is not close enough to unlock."}
    if simulation.door_unlocked:
        return {"success": False, "reason": "Door is already unlocked."}

    simulation.door_unlocked = True
    return {
        "success": True,
        "door_unlocked": True,
        "door_position": list(simulation.door_position),
    }


def send_message(simulation: Any, agent_id: str, agent: str, message: dict[str, Any]) -> dict[str, Any]:
    simulation.message_queue.append(
        {
            "from": agent_id,
            "to": agent,
            "message": message,
            "deliver_on_turn": simulation.turn_index + 1,
        }
    )
    return {"success": True, "queued_for": agent, "message": message}


def _adjacent_or_same(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 1
