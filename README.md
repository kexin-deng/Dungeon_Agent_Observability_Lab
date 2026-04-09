
A lightweight multi-agent simulation system for tracing, debugging, and analyzing agent behavior in partially observable environments.

---

## 🎯 Project Goal

This project focuses on **observability and debugging**, rather than solving the environment optimally.

Agents operate in a simple dungeon environment while the system captures structured traces to answer:

* What happened?
* Why did it happen?
* What should change?

---

## 🧩 Environment Setup

* Grid: **8 × 8**
* Agents: **2**
* Objects:

  * Key (1)
  * Door (1, initially locked)
  * Exit (1)
  * Obstacles (random walls)

### Rules

* Agents have **partial observability** (adjacent cells only)
* One agent must pick up the key and unlock the door
* **Door unlock is global**: once unlocked, all agents can pass
* Goal: **both agents reach the exit**

---

## 🤖 Agent Design

Agents are intentionally simple:

* Turn-based actions
* Local observations only
* Limited tool set:

  * `move(direction)`
  * `look()`
  * `pick_up(item)`
  * `use_item(item, target)`
  * `send_message(agent, message)`

> Agents are not optimized for performance — failures and inefficiencies are expected and used for analysis.

---

## 📊 Observability & Tracing

Each step logs structured data including:

* step number
* agent id
* observation
* action + result
* belief state
* messages
* environment state (e.g. `door_unlocked`)
* latency breakdowns
* Langfuse trace metadata

### Langfuse Integration

The project includes an optional Langfuse integration for end-to-end tracing.

It captures:

* agent decisions
* tool calls
* reasoning input/output
* belief evolution
* environment transitions
* step latency
* tool latency
* reasoning / LLM latency

When the `langfuse` package is installed and `LANGFUSE_PUBLIC_KEY` plus `LANGFUSE_SECRET_KEY` are set, the simulation emits trace/span data to Langfuse. Without those dependencies, the same fields are still written into the local JSON trace so local debugging continues to work.

Example:

```json
{
  "step": 22,
  "agent": "A",
  "action": "use_item",
  "result": "door_unlocked",
  "belief": {
    "has_key": true,
    "door_position": [6, 0]
  }
}
```

---

## 🧠 Belief Tracking

Each agent maintains a belief state:

* object locations (key, door, exit)
* whether it has the key
* visited positions
* teammate status

This enables detection of:

* stale beliefs
* incorrect assumptions
* coordination gaps

---

## ⚠️ Failure & Behavior Analysis

The system surfaces meaningful patterns beyond raw logs:

### 1. Loop / Inefficiency Detection

Example:

```text
Agent A revisited [6, 0] 12 times
```

Indicates inefficient exploration or local policy failure.

---

### 2. Coordination Gaps

* Agents may fail to act on shared information
* Message passing may not result in correct behavior

---

### 3. Termination Issue (Observed)

Even after both agents reached the exit:

```text
step 14: Agent A reached the exit
step 29: Agent B reached the exit
Run status: max_steps_reached
```

The simulation did not terminate early.

This indicates a missing or delayed termination condition.

---

## 🧾 Summary Output

Each run produces:

### What happened

```text
- step 3: Agent A picked up the key
- step 22: Agent A unlocked the door
- step 29: Agent B reached the exit
```

---

### Why it happened

```text
- Agents completed objectives successfully
- However, both agents exhibited inefficient behavior:
  - repeated visits to the same locations
- System lacks early termination after success
```

---

### What should change

```text
- Add termination condition when both agents reach exit
- Reduce repeated visits via simple heuristics
- Improve coordination awareness
```

---

## 🖥️ Visualization

A simple, lightweight interface is used:

```
[ GRID ]              [ LOGS ]

. . . . . . . .
. A . . # . . .
. . . K . . . .
. . # . . . . .
. . . . D . . .
. . . . . . . .
. . . . . . B .
. . . . . . . E
```

* Left: environment state
* Right: agent decision trace

---

## 🏗️ System Design

```
simulation.py → world + game loop  
agents.py     → agent logic  
tools.py      → environment interaction  
logger.py     → structured logging  
main.py       → entry point  
```

---

## 🤖 AI-Assisted Development

This project was built using a structured AI workflow:

* **ChatGPT**: prompt design and system framing
* **Claude**: system design and reasoning
* **Codex**: code implementation and debugging
* **Human**: orchestration, validation, and refinement

> AI outputs were reviewed and selectively adopted rather than blindly accepted.

---

## 🚀 Key Takeaways

* The dungeon is not the point — **traces are the point**
* Observability enables understanding of agent behavior
* Simple systems can still produce rich failure modes
* Debugging multi-agent systems requires:

  * state consistency
  * belief tracking
  * behavior analysis

I visualize full agent execution traces in Langfuse, including:
- step-level decisions
- reasoning vs tool execution
- latency breakdown
- failure patterns (loops, belief mismatch)
