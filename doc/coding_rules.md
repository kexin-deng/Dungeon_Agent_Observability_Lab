Coding Standard

## Purpose

This document defines the coding and system design constraints for building the Dungeon Agent Observability Lab using AI coding tools (Claude Code, Codex).

It ensures consistency, traceability, and alignment with project goals.

## AI Usage Strategy

- ChatGPT is used for generating prompts and coding_rules file and guiding setup.
- Claude is used for system design and reasoning
- Codex is used for code implementation
- Human reviews, edits, and overrides outputs

## Python Rule

You are helping me build a small multi-agent simulation system for debugging and observability.

IMPORTANT:
This is NOT a game optimization problem. The goal is NOT to solve the dungeon efficiently.
The goal is to generate structured traces and make agent behavior understandable and debuggable.

Please follow ALL requirements carefully.

--------------------------------------------------
PROJECT GOAL
--------------------------------------------------

Build a lightweight simulation where two AI agents explore a dungeon together.

The system must:
1. Simulate a simple grid-based dungeon
2. Let agents act step-by-step using tools
3. Log structured traces of every decision
4. Enable post-run analysis of what happened and why

Focus on:
- trace quality
- observability
- debugging agent behavior

NOT focus on:
- optimal policies
- complex game mechanics

--------------------------------------------------
SIMULATION REQUIREMENTS
--------------------------------------------------

World:
- Grid size: 8x8
- Include:
  - key * 1
  - locked door * 1
  - exit * 1
  - Obstacles: 5–8 random walls
- Agents start at random positions
- Fog of war:
  - each agent only sees adjacent cells

Objective:
- Both agents must reach the exit
- At least one agent must use the key to unlock the door

--------------------------------------------------
AGENT DESIGN
--------------------------------------------------

Each agent:
- Acts in turns
- Has limited local observation
- Uses tools to interact with environment

Tool set:
- move(direction) → move one cell
- look() → observe nearby cells
- pick_up(item)
- check_inventory()
- use_item(item, target)
- send_message(agent, message)

Important:
- Agents do NOT need to be smart
- Simple or even imperfect behavior is fine
- Do NOT over-engineer planning

--------------------------------------------------
GAME LOOP
--------------------------------------------------

For each step:
1. Get agent observation
2. Agent decides action
3. Execute tool
4. Update world state
5. Log everything

Notes:
- Agents take turns
- Messages are delivered with delay (next turn)
- End conditions:
  - success
  - max steps reached
  - agents stuck

--------------------------------------------------
TRACE / LOGGING REQUIREMENTS (VERY IMPORTANT)
--------------------------------------------------

You MUST implement structured logging.

Each step log must include:

- step number
- agent id
- observation
- thought / reasoning (if available)
- action (tool call)
- tool input
- tool output
- result / new state
- latency (optional)
- belief state (if implemented)

Additionally:
- Log full history across the run
- Export logs as JSON

--------------------------------------------------
BELIEF TRACKING (IMPORTANT FEATURE)
--------------------------------------------------

Each agent should maintain a simple belief state:

Examples:
- where key is
- where door is
- whether it has key

Log:
- belief state
- ground truth

This allows detecting:
- stale beliefs
- incorrect assumptions

--------------------------------------------------
FAILURE / DEBUGGING SUPPORT
--------------------------------------------------

The system should help identify:

- incorrect tool usage
- repeated actions / loops
- belief vs reality mismatch
- coordination failures

Do NOT just log errors.
Surface meaningful patterns.

--------------------------------------------------
LEGIBILITY LAYER (CRITICAL)
--------------------------------------------------

Build a simple analysis tool that answers:

1. What happened?
2. Why did it happen?
3. What should change?

Examples:
- timeline of events
- key failure moments
- belief divergence

Keep it simple (print or basic visualization is fine).

--------------------------------------------------
CODE STRUCTURE
--------------------------------------------------

Organize code clearly:

- simulation.py → world + loop
- agents.py → agent logic
- tools.py → tool functions
- logger.py → structured logging
- main.py → entry point

Keep code modular and readable.

--------------------------------------------------
IMPLEMENTATION STRATEGY
--------------------------------------------------

Start simple:
1. Basic grid + movement
2. Add agents
3. Add logging
4. Add belief tracking
5. Add analysis

Do NOT try to build everything at once.

--------------------------------------------------
OUTPUT
--------------------------------------------------

Provide:
1. Clean Python implementation
2. Clear function structure
3. Example run
4. Example trace JSON

--------------------------------------------------
IMPORTANT STYLE RULES
--------------------------------------------------

- Keep code simple and readable
- Prefer clarity over cleverness
- Avoid unnecessary abstraction
- Add comments explaining design decisions

## Visualization Layout

- Use a simple two-panel layout:
  - Left: grid world (current state)
  - Right: agent logs for current step

Grid:
- ASCII-based visualization
- Fixed size (8x8)
- Symbols:
  - A/B: agents
  - K: key
  - D: door
  - E: exit
  - #: obstacle

Log panel:
- agent id
- observation
- action
- result
- belief state
- message

Goal:
Ensure a human can quickly understand what happened at each step.

--------------------------------------------------
FINAL NOTE
--------------------------------------------------

This is an observability system disguised as a simulation.

Prioritize:
- trace quality
- interpretability
- debugging capability

Not:
- agent intelligence

## Tracking Rule (comes later)