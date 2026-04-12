const AGENT_EMOJI = {
  A: "👨",
  B: "👩"
};

const BULLETIN_ICONS = {
  key: "🔑",
  door: "🚪",
  exit: "🏁"
};

function toKey(position) {
  return position ? `${position[0]},${position[1]}` : "";
}

function formatPosition(position) {
  return position ? `(${position[0]}, ${position[1]})` : "unknown";
}

function summarizeObservation(observation) {
  return observation.visible_cells
    .map((cell) => {
      const position = `(${cell.position[0]}, ${cell.position[1]})`;
      if (cell.cell_type === "door") {
        return `${position}: door ${cell.door_unlocked ? "unlocked" : "locked"}`;
      }
      if (cell.cell_type === "agent") {
        return `${position}: agent ${cell.agent_id}`;
      }
      return `${position}: ${cell.cell_type}`;
    })
    .join(", ");
}

function summarizeAction(step) {
  const args = Object.entries(step.tool_input || {})
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join(", ");
  return args ? `${step.action}(${args})` : `${step.action}()`;
}

function summarizeChatAction(step) {
  if (step.action === "move") {
    return `moves ${step.tool_input.direction}`;
  }
  if (step.action === "pick_up") {
    return `picks up the ${step.tool_input.item}`;
  }
  if (step.action === "use_item") {
    return `uses the ${step.tool_input.item} on the ${step.tool_input.target}`;
  }
  if (step.action === "send_message") {
    return `sends a message to Agent ${step.tool_input.agent}`;
  }
  if (step.action === "look") {
    return "scans the nearby area";
  }
  return summarizeAction(step).replaceAll("_", " ");
}

function summarizeResult(step) {
  const output = step.tool_output || {};
  if (output.success === false) {
    return output.reason || "The action fails.";
  }
  if (step.action === "move" && output.position) {
    return `arrives at ${formatPosition(output.position)}`;
  }
  if (step.action === "pick_up" && output.inventory) {
    return "secures the key.";
  }
  if (step.action === "use_item" && output.door_unlocked) {
    return `unlocks the door at ${formatPosition(output.door_position)}`;
  }
  if (step.action === "send_message") {
    return `the note is queued for Agent ${output.queued_for}`;
  }
  if (step.action === "look") {
    return `spots ${output.visible_cells?.length || 0} nearby cells`;
  }
  return "completes the action successfully.";
}

function summarizeBelief(step) {
  const belief = step.belief_state || {};
  const key = belief.key_position ? formatPosition(belief.key_position) : "unknown";
  const door = belief.door_position ? formatPosition(belief.door_position) : "unknown";
  const exit = belief.exit_position ? formatPosition(belief.exit_position) : "unknown";
  return `key -> ${key}, door -> ${door}, exit -> ${exit}, has_key -> ${belief.has_key ? "yes" : "no"}`;
}

function summarizeMessage(step) {
  const messages = step.delivered_messages || [];
  if (!messages.length) {
    return "";
  }
  return messages
    .map((message) => {
      if (message.kind === "location_update") {
        return `${message.from}: ${message.item} at ${formatPosition(message.position)}`;
      }
      return `${message.from}: status update`;
    })
    .join(" | ");
}

function summarizeChatThought(step) {
  if (step.thought) {
    return step.thought
      .replace(/^I will /, "I'll ")
      .replace(/^I am /, "I'm ")
      .replace(/^I learned something useful and should share it with my teammate\./, "I found something worth sharing.")
      .replace(/^The locked door is nearby and I have the key, so I should unlock it\./, "I have the key, so this is the moment to open the door.")
      .replace(/^I am standing on the key, so I should pick it up\./, "The key is right here, so I should grab it.")
      .replace(/^I am uncertain about the next move, so I will refresh my local observation\./, "I need a quick read on the area before committing.");
  }
  return "I am reacting to the world one step at a time.";
}

function summarizeChatBelief(step) {
  const belief = step.belief_state || {};
  const key = belief.key_position ? formatPosition(belief.key_position) : "unknown";
  const door = belief.door_position ? formatPosition(belief.door_position) : "unknown";
  return `key -> ${key}, door -> ${door}, has_key -> ${belief.has_key ? "yes" : "no"}`;
}

function collectHighlights(step) {
  const highlights = [];
  const output = step.tool_output || {};
  if (step.anomaly?.type === "loop") {
    highlights.push({
      icon: "🔁",
      kind: "loop",
      level: "warning",
      title: "LOOP DETECTED",
      text: `Agent ${step.agent_id} revisited ${formatPosition(step.anomaly.position)} ${step.anomaly.count} times`
    });
  }
  if (output.success === false) {
    highlights.push({
      icon: "❌",
      kind: "failure",
      level: "critical",
      title: "ACTION FAILED",
      text: `Agent ${step.agent_id}: ${output.reason || "Failed tool usage"}`
    });
  }

  const belief = step.belief_state || {};
  const truth = step.ground_truth || {};
  if (
    belief.key_position &&
    truth.key_position &&
    toKey(belief.key_position) !== toKey(truth.key_position)
  ) {
    highlights.push({
      icon: "⚠",
      kind: "belief_mismatch",
      level: "warning",
      title: "BELIEF MISMATCH",
      text: `Agent ${step.agent_id} still believes the key is at ${formatPosition(belief.key_position)}`
    });
  }

  if ((step.delivered_messages || []).length && step.action === "look") {
    highlights.push({
      icon: "🤝",
      kind: "coordination",
      level: "info",
      title: "COORDINATION LAG",
      text: `Agent ${step.agent_id} received a message but kept observing instead of acting`
    });
  }

  return highlights;
}

function parseAgentId(description) {
  const match = description.match(/Agent ([AB])/);
  return match ? match[1] : null;
}

function buildMilestones(rawTrace, replayMetadata) {
  const milestones = [];
  const majorEvents = rawTrace.summary?.major_events || [];

  majorEvents.forEach((event) => {
    const agentId = parseAgentId(event.description);
    if (!agentId) {
      return;
    }

    if (event.description.includes("picked up the key")) {
      milestones.push({
        step: event.step,
        type: "key",
        agentId,
        icon: BULLETIN_ICONS.key,
        text: `Agent ${agentId} got the key`
      });
    }

    if (event.description.includes("unlocked the door")) {
      milestones.push({
        step: event.step,
        type: "door",
        agentId,
        icon: BULLETIN_ICONS.door,
        text: `Agent ${agentId} reached the door and unlocked it`
      });
    }

    if (event.description.includes("reached the exit")) {
      milestones.push({
        step: event.step,
        type: "exit",
        agentId,
        icon: BULLETIN_ICONS.exit,
        text: `Agent ${agentId} reached the exit`
      });
    }
  });

  const doorPosition = replayMetadata.door_position;
  if (doorPosition) {
    let firstDoorTouch = null;
    rawTrace.steps.some((step) => {
      const match = Object.entries(step.ground_truth.agent_positions).find(
        ([, position]) => position[0] === doorPosition[0] && position[1] === doorPosition[1]
      );
      if (!match) {
        return false;
      }
      firstDoorTouch = {
        step: step.step,
        type: "door",
        agentId: match[0],
        icon: BULLETIN_ICONS.door,
        text: `Agent ${match[0]} reached the door`
      };
      return true;
    });

    if (firstDoorTouch && !milestones.some((item) => item.type === "door")) {
      milestones.push(firstDoorTouch);
    }
  }

  return milestones.sort((left, right) => left.step - right.step);
}

export function parseLogs(rawTrace) {
  const firstStep = rawTrace.steps[0];
  const derivedReplayMetadata = {
    grid_size: 8,
    walls: Array.from(
      new Set(
        rawTrace.steps.flatMap((step) =>
          (step.belief_state?.walls || []).map((position) => `${position[0]},${position[1]}`)
        )
      )
    ).map((positionKey) => positionKey.split(",").map(Number)),
    key_position: firstStep?.ground_truth?.key_position || null,
    door_position: firstStep?.ground_truth?.door_position || null,
    exit_position: firstStep?.ground_truth?.exit_position || null
  };
  const replayMetadata = rawTrace.summary.replay_metadata || derivedReplayMetadata;
  const wallSet = new Set(replayMetadata.walls.map(([row, col]) => `${row},${col}`));
  const milestones = buildMilestones(rawTrace, replayMetadata);
  const trailHistory = {
    A: [],
    B: []
  };
  const hasKeyByAgent = {
    A: false,
    B: false
  };
  const previousPositions = {
    A: null,
    B: null
  };
  const langfuseTraceUrl = rawTrace.summary?.observability?.trace_url || null;

  const frames = rawTrace.steps.map((step, index) => {
    hasKeyByAgent[step.agent_id] = Boolean(step.belief_state.has_key);
    const snapshotPreviousPositions = {
      A: previousPositions.A,
      B: previousPositions.B
    };
    Object.entries(step.ground_truth.agent_positions).forEach(([agentId, position]) => {
      const positionKey = toKey(position);
      const currentTrail = trailHistory[agentId];
      const lastPositionKey = currentTrail[currentTrail.length - 1];
      if (lastPositionKey !== positionKey) {
        trailHistory[agentId] = [...currentTrail, positionKey].slice(-5);
      }
    });

    const agentPositionLookup = {};
    const agentCards = Object.entries(step.ground_truth.agent_positions).map(([agentId, position]) => {
      const key = toKey(position);
      agentPositionLookup[key] = agentId;
      return {
        agentId,
        hasKey: hasKeyByAgent[agentId],
        positionLabel: formatPosition(position)
      };
    });

    const visibleTiles = step.observation.visible_cells.map((cell) => toKey(cell.position));
    const thought = step.thought || "No explicit reasoning captured.";
    const chatAction = summarizeChatAction(step);
    const chatResult = summarizeResult(step);
    const chatBelief = summarizeChatBelief(step);
    const chatMessage = summarizeMessage(step);
    const storyActionLine = `→ ${chatAction}`;
    const storyResultLine = `→ ${chatResult}`;
    const storyBeliefLine = `believes ${chatBelief}`;
    const storyMessageLine = chatMessage ? `hears ${chatMessage}` : "";

    const trailPaths = Object.fromEntries(
      Object.entries(trailHistory).map(([agentId, positions]) => [
        agentId,
        positions.map((positionKey) => positionKey.split(",").map(Number))
      ])
    );
    const bulletinItems = milestones.filter((item) => item.step <= step.step);

    const frame = {
      action: step.action,
      actionLabel: summarizeAction(step),
      agentCards,
      agentEmoji: AGENT_EMOJI[step.agent_id],
      agentName: step.agent_id === "A" ? "Agent A" : "Agent B",
      agentId: step.agent_id,
      agentPositionLookup,
      beliefLabel: summarizeBelief(step),
      chatAction,
      chatBelief,
      chatMessage,
      chatResult,
      chatThought: summarizeChatThought(step),
      deliveredMessages: step.delivered_messages,
      doorUnlocked: Boolean(step.environment_state.door_unlocked),
      highlights: collectHighlights(step),
      id: `${step.step}-${step.agent_id}-${index}`,
      index,
      keyPicked: Boolean(step.ground_truth.key_picked),
      keyPositionKey: step.ground_truth.key_position ? toKey(step.ground_truth.key_position) : "",
      latencyLabel: `${step.latency_ms?.toFixed?.(1) || step.latency_ms || 0} ms`,
      messageLabel: summarizeMessage(step),
      observationLabel: summarizeObservation(step.observation),
      previousPositions: snapshotPreviousPositions,
      resultLabel: chatResult,
      step: step.step,
      storyActionLine,
      storyBeliefLine,
      storyMessageLine,
      storyResultLine,
      bulletinItems,
      thought,
      toolInput: step.tool_input || {},
      trailPaths,
      visibleTiles,
      agentPositions: step.ground_truth.agent_positions
    };
    Object.entries(step.ground_truth.agent_positions).forEach(([agentId, position]) => {
      previousPositions[agentId] = position;
    });
    return frame;
  });

  return {
    frames,
    replayMetadata: {
      keyKey: toKey(replayMetadata.key_position),
      doorKey: toKey(replayMetadata.door_position),
      exitKey: toKey(replayMetadata.exit_position),
      gridSize: replayMetadata.grid_size,
      wallSet
    },
    runId: rawTrace.run_id,
    summary: rawTrace.summary,
    traceHref: langfuseTraceUrl || "./artifacts/latest_trace.json",
    hasLangfuseTrace: Boolean(langfuseTraceUrl)
  };
}
