import React from "react";

const TILE_EMOJI = {
  wall: "🪨",
  key: "🔑",
  doorLocked: "🚪",
  doorUnlocked: "🚪",
  exit: "🏁",
  A: "👨",
  B: "👩"
};

const DIRECTION_ARROW = {
  up: "↑",
  down: "↓",
  left: "←",
  right: "→"
};

const TRAIL_OPACITY = [0.4, 0.55, 0.7, 0.85, 1.0];
const AGENT_COLORS = {
  A: "#4FC3F7",
  B: "#F48FB1"
};

function tileKey(row, col) {
  return `${row},${col}`;
}

function toPercent(position, gridSize) {
  const tileSize = 100 / gridSize;
  return {
    left: position[1] * tileSize,
    top: position[0] * tileSize,
    tileSize
  };
}

function renderTrailDots(agentId, points, gridSize) {
  const recentPoints = points.slice(-5);
  return recentPoints.map((position, index) => {
    const { left, top, tileSize } = toPercent(position, gridSize);
    const opacity = TRAIL_OPACITY[index];
    return (
      <div
        key={`${agentId}-${position[0]}-${position[1]}-${index}`}
        className={`trail-dot trail-dot-${agentId.toLowerCase()}`}
        style={{
          "--trail-opacity": opacity,
          "--trail-color": AGENT_COLORS[agentId],
          "--trail-glow": 4 + index * 2,
          width: `${tileSize * 0.48}%`,
          height: `${tileSize * 0.48}%`,
          left: `calc(${left}% + ${tileSize * 0.26}%)`,
          top: `calc(${top}% + ${tileSize * 0.26}%)`
        }}
      />
    );
  });
}

function renderTrailSegments(agentId, points, gridSize) {
  const recentPoints = points.slice(-5);
  if (recentPoints.length < 2) {
    return null;
  }

  return recentPoints.slice(1).map((position, index) => {
    const previous = recentPoints[index];
    const manhattanDistance =
      Math.abs(previous[0] - position[0]) + Math.abs(previous[1] - position[1]);
    if (manhattanDistance !== 1) {
      return null;
    }
    const current = position;
    const start = toPercent(previous, gridSize);
    const end = toPercent(current, gridSize);
    const x1 = start.left + start.tileSize / 2;
    const y1 = start.top + start.tileSize / 2;
    const x2 = end.left + end.tileSize / 2;
    const y2 = end.top + end.tileSize / 2;
    const opacity = TRAIL_OPACITY[index + 1];

    return (
      <line
        key={`${agentId}-segment-${index}-${previous.join("-")}-${current.join("-")}`}
        className={`trail-segment trail-segment-${agentId.toLowerCase()}`}
        style={{
          "--trail-opacity": opacity,
          "--trail-color": AGENT_COLORS[agentId],
          "--trail-glow": 3 + (index + 1) * 1.5
        }}
        x1={x1}
        x2={x2}
        y1={y1}
        y2={y2}
      />
    );
  });
}

function normalizeTrailPoints(points) {
  return points.filter((position, index) => {
    if (index === 0) {
      return true;
    }
    const previous = points[index - 1];
    return previous[0] !== position[0] || previous[1] !== position[1];
  });
}

export default function GridPanel({ frame, replayMetadata }) {
  const cells = [];
  const gridSize = replayMetadata.gridSize;
  const trailPaths = frame.trailPaths || { A: [], B: [] };
  const currentActiveKey = frame.agentPositions?.[frame.agentId]
    ? tileKey(frame.agentPositions[frame.agentId][0], frame.agentPositions[frame.agentId][1])
    : "";
  const movementArrow =
    frame.action === "move" ? DIRECTION_ARROW[frame.toolInput.direction] : "";

  for (let row = 0; row < gridSize; row += 1) {
    for (let col = 0; col < gridSize; col += 1) {
      const key = tileKey(row, col);
      const wall = replayMetadata.wallSet.has(key);
      const isDoor = key === replayMetadata.doorKey;
      const isExit = key === replayMetadata.exitKey;
      const isKey = replayMetadata.keyKey === key;
      const agentId = frame.agentPositionLookup[key];
      const isActiveAgentTile = currentActiveKey === key;
      const unlock = frame.action === "use_item" && isDoor ? "unlock-door" : "";
      const flash = frame.action === "pick_up" && isKey ? "flash-key" : "";
      const movementPulse = isActiveAgentTile && frame.action === "move" ? "movement-pulse" : "";

      let worldContent = null;
      if (wall) {
        worldContent = <span className="tile-object wall-object">{TILE_EMOJI.wall}</span>;
      } else if (isKey) {
        worldContent = (
          <span className={frame.keyPicked ? "tile-object key-object key-picked" : "tile-object key-object"}>
            {TILE_EMOJI.key}
          </span>
        );
      } else if (isDoor) {
        worldContent = (
          <span className="tile-object door-object">
            {frame.doorUnlocked ? TILE_EMOJI.doorUnlocked : `${TILE_EMOJI.doorLocked}🔒`}
          </span>
        );
      } else if (isExit) {
        worldContent = <span className="tile-object exit-object">{TILE_EMOJI.exit}</span>;
      }

      let agentContent = null;
      if (agentId) {
        agentContent = (
          <div
            className={[
              "tile-agent-token",
              `tile-agent-token-${agentId.toLowerCase()}`,
              isActiveAgentTile ? "is-active" : ""
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="agent-token-emoji">{TILE_EMOJI[agentId]}</span>
            {isActiveAgentTile && movementArrow ? (
              <span className="tile-arrow agent-arrow">{movementArrow}</span>
            ) : null}
          </div>
        );
      }

      cells.push(
        <div
          key={key}
          className={[
            "grid-tile",
            wall ? "wall-tile" : "floor-tile",
            movementPulse,
            flash,
            unlock
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <div className="tile-texture" />
          <div className="world-object-layer">{worldContent}</div>
          <div className="agent-object-layer">{agentContent}</div>
        </div>
      );
    }
  }

  return (
    <section className="panel grid-panel">
      <div className="panel-header narrative-header">
        <p className="panel-label">Grid Replay</p>
        <div className="step-callout">
          <p className="step-kicker">STEP {frame.step}</p>
          <h2>
            {TILE_EMOJI[frame.agentId]} {frame.agentName} is acting
          </h2>
          <p className="step-action-line">{frame.storyActionLine}</p>
        </div>
      </div>

      <div className="agent-status-row">
        {frame.agentCards.map((card) => (
          <article
            key={card.agentId}
            className={[
              "agent-status",
              card.agentId === frame.agentId ? "active" : "",
              card.agentId === frame.agentId ? `active-${card.agentId.toLowerCase()}` : ""
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="agent-avatar">{TILE_EMOJI[card.agentId]}</span>
            <div>
              <strong>{card.agentId === "A" ? "Explorer A" : "Partner B"}</strong>
              <p>
                Pos {card.positionLabel} · {card.hasKey ? "Has key" : "No key"}
              </p>
            </div>
          </article>
        ))}
      </div>

      <div className="grid-scene">
        <div
          className="grid-board"
          style={{ gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))` }}
        >
          {cells}
        </div>

        <svg className="trail-lines-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
          {Object.entries(trailPaths).map(([agentId, points]) => (
            <g key={agentId}>
              {renderTrailSegments(agentId, normalizeTrailPoints(points), gridSize)}
            </g>
          ))}
        </svg>

        <div className="trail-dots-layer">
          {Object.entries(trailPaths).map(([agentId, points]) =>
            renderTrailDots(agentId, normalizeTrailPoints(points), gridSize)
          )}
        </div>
      </div>

      <div className="bulletin-board" aria-live="polite">
        <div className="bulletin-board-header">
          <p className="panel-label">Bulletin Board</p>
          <span className="bulletin-subtitle">Major progress in this run</span>
        </div>
        <div className="bulletin-items">
          {frame.bulletinItems?.length ? (
            frame.bulletinItems.map((item) => (
              <article
                key={`${item.type}-${item.agentId}-${item.step}`}
                className={`bulletin-item bulletin-${item.type}`}
              >
                <span className="bulletin-icon">{item.icon}</span>
                <div>
                  <strong>{item.text}</strong>
                  <p>Step {item.step}</p>
                </div>
              </article>
            ))
          ) : (
            <article className="bulletin-item bulletin-pending">
              <span className="bulletin-icon">📌</span>
              <div>
                <strong>No major milestone yet</strong>
                <p>The agents are still exploring the dungeon.</p>
              </div>
            </article>
          )}
        </div>
      </div>

      <div className="grid-caption">
        <span>Dungeon map with 5-step memory trail</span>
        <span>{frame.storyResultLine}</span>
      </div>
    </section>
  );
}
