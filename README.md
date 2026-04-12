# Dungeon Agent Observability Lab

A lightweight observability sandbox for multi-agent behavior in a partially observable dungeon.

This project is not about building the smartest dungeon solver. It is about making agent behavior inspectable:

- what each agent saw
- what it believed
- what it decided
- what tool actually executed
- where coordination broke down

## What It Does

Each run generates a fresh dungeon episode:

- `8 x 8` grid
- `2` agents
- `1` key
- `1` locked door
- `1` exit
- random interior obstacles
- fog of war: each agent only sees its own tile plus adjacent tiles

The task is:

1. find the key
2. unlock the door
3. get both agents to the exit

The system records structured step-by-step traces and exposes them through:

- terminal rendering
- local JSON trace export
- optional Langfuse tracing
- a React replay UI with a live grid + narrative log stream

## Current Replay UI

The replay frontend is driven by `artifacts/latest_trace.json` and includes:

- left panel: live grid replay
- right panel: streaming narrative log panel
- step playback controls
- timeline slider
- 5-step colored movement trail
- bulletin board under the grid for key milestones
- run facts panel under the logs
- clickable Langfuse trace link when available

The grid currently shows:

- persistent world objects
- trail overlay
- agents on top
- replay-focused visual hierarchy

## Project Structure

```text
agents.py         agent policy and belief updates
simulation.py     world generation, turn loop, summary building
tools.py          environment tools (move, look, pick_up, use_item, send_message, ...)
logger.py         structured step logging and JSON export
observability.py  optional Langfuse tracer wrapper
main.py           entry point, run orchestration, replay auto-launch
replay_server.py  local static server for the built replay UI
frontend/         React + Vite replay interface
artifacts/        exported traces
```

## Agent Model

Agents are intentionally simple and traceable rather than optimized.

Each agent has:

- local observation only
- lightweight belief state
- recent action memory
- teammate messaging
- basic spatial exploration and target selection

Supported tools:

- `move(direction)`
- `look()`
- `pick_up(item)`
- `check_inventory()`
- `use_item(item, target)`
- `send_message(agent, message)`

Belief state tracks things like:

- known key location
- known door location
- known exit location
- whether the agent has the key
- known walls
- visit counts / revisits
- teammate status from messages

## Logging And Analysis

Each logged step includes structured fields such as:

- step number
- agent id
- observation
- thought
- action
- tool input
- tool output
- result state
- belief state
- ground truth snapshot
- environment state
- delivered messages
- anomaly metadata
- latency breakdowns
- Langfuse step metadata

Each run also produces a summary with:

- run status
- step count
- door state
- whether agents reached the exit
- replay metadata for the frontend
- major events
- loop anomalies
- observability metadata including Langfuse URL when enabled

The analysis layer surfaces:

- major events such as key pickup, door unlock, exit arrival
- repeated-position loop anomalies
- belief mismatches
- coordination lag signals

## Langfuse Integration

Langfuse is optional.

If the `langfuse` package is installed and the following env vars are available:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- optionally `LANGFUSE_HOST`

the simulation emits traces and spans to Langfuse.

The exported local trace still contains observability metadata even if Langfuse is unavailable, so the replay UI and JSON inspection continue to work locally.

When Langfuse is enabled, the run summary contains:

- `trace_id`
- `trace_url`
- init status
- Python executable
- flush settings

## How To Run

### 1. Install Python dependencies

Use your environment of choice and install the project requirements you need. At minimum, the simulation runs with the local Python files in this repo. For Langfuse export, install the `langfuse` package and configure credentials.

### 2. Build the replay UI

```bash
npm install
npm run build
```

### 3. Run the simulation

```bash
python3 main.py
```

This will:

- generate a fresh episode
- write `artifacts/latest_trace.json`
- print the terminal summary
- start the local replay server if `frontend/dist` exists
- open the replay UI in the browser when possible

The replay server runs on:

```text
http://127.0.0.1:8123
```

## Trace Output

The canonical local trace file is:

```text
artifacts/latest_trace.json
```

It includes both:

- the full per-step history
- the summary block consumed by the replay UI

Replay metadata includes:

- grid size
- walls
- key position
- door position
- exit position
- initial agent positions

## Success And Failure Conditions

The simulation can end with:

- `success`
- `agents_stuck`
- `max_steps_reached`

Success currently means:

- the door is unlocked
- both agents are standing on the exit

## Current Behavior Notes

The current implementation intentionally keeps the agents simple enough to produce interesting traces:

- they can loop
- they rely on partial information
- they communicate imperfectly
- they are readable, not optimal

Some recent improvements already in the codebase:

- run ends successfully when both agents reach the exit after the door is unlocked
- agents do not wander after reaching the exit unless key-handling logic still requires progress
- replay UI shows a 5-step movement trail for each agent
- replay footer links to the Langfuse trace URL when available

## Frontend Stack

The replay UI uses:

- React 18
- Vite 5

Frontend entry points live under `frontend/src/`.

## Development Notes

This project was developed iteratively with AI-assisted tooling and human review. The emphasis throughout is:

- observability over optimization
- replayability over sophistication
- clarity over cleverness

## Quick Takeaway

This is an observability system disguised as a dungeon simulation.

The dungeon is just the stage. The real output is the trace.
