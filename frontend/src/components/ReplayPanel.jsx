import React, { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage.jsx";

export default function ReplayPanel({
  currentFrame,
  frames,
  onJumpToFrame,
  replayMetadata,
  traceHref,
  hasLangfuseTrace
}) {
  const visibleFrames = frames.slice(0, currentFrame.index + 1);
  const scrollerRef = useRef(null);
  const loopFrames = frames.filter((frame) => frame.highlights.some((item) => item.kind === "loop"));
  const failureFrames = frames.filter((frame) =>
    frame.highlights.some((item) => item.kind === "failure" || item.kind === "belief_mismatch")
  );

  useEffect(() => {
    const node = scrollerRef.current;
    if (!node) {
      return;
    }
    node.scrollTo({
      top: node.scrollHeight,
      behavior: "smooth"
    });
  }, [currentFrame.index]);

  return (
    <section className="panel replay-panel">
      <div className="panel-header">
        <p className="panel-label">Streaming Logs</p>
        <h2>Narrative reasoning stream</h2>
      </div>

      <div className="event-strip">
        {loopFrames[0] ? (
          <button className="event-chip warning" onClick={() => onJumpToFrame(loopFrames[0].index)} type="button">
            ⚠ LOOP DETECTED · jump to step {loopFrames[0].step}
          </button>
        ) : null}
        {failureFrames[0] ? (
          <button
            className="event-chip critical"
            onClick={() => onJumpToFrame(failureFrames[0].index)}
            type="button"
          >
            ❌ FAILURE MOMENT · jump to step {failureFrames[0].step}
          </button>
        ) : null}
      </div>

      <div className="shortcut-card">
        <p className="shortcut-title">Controls</p>
        <div className="shortcut-grid">
          <span>→ : Next step</span>
          <span>← : Previous step</span>
          <span>Space : Play / Pause</span>
          <span>R : Restart replay</span>
        </div>
      </div>

      <div className="chat-feed" ref={scrollerRef}>
        {visibleFrames.map((frame, index) => (
          <ChatMessage
            frame={frame}
            isLatest={index === visibleFrames.length - 1}
            key={frame.id}
          />
        ))}
      </div>

      <div className="run-facts-card">
        <p className="shortcut-title">Run Facts</p>
        <div className="run-facts-grid">
          <div className="run-fact-block">
            <p className="run-fact-heading">🧱 Grid</p>
            <p className="run-fact-line">Size: {replayMetadata.gridSize} × {replayMetadata.gridSize}</p>
          </div>

          <div className="run-fact-block">
            <p className="run-fact-heading">👨👩 Agents</p>
            <p className="run-fact-line">Count: 2</p>
          </div>

          <div className="run-fact-block">
            <p className="run-fact-heading">🧩 Objects</p>
            <p className="run-fact-line">🚪 Doors: 1</p>
            <p className="run-fact-line">🔑 Keys: 1</p>
            <p className="run-fact-line">🪨 Obstacles: {replayMetadata.wallSet.size}</p>
            <p className="run-fact-line">🏁 Exit: 1</p>
          </div>

          <div className="run-fact-block">
            <p className="run-fact-heading">⚙️ Rules</p>
            <p className="run-fact-line">Movement: 4-directional</p>
            <p className="run-fact-line">Memory: 5-step trail</p>
          </div>

          <div className="run-fact-block">
            <p className="run-fact-heading">🎮 Mode</p>
            <p className="run-fact-line">Simulation: Real-time</p>
            <p className="run-fact-line">Visibility: Full grid</p>
          </div>
        </div>

        <a className="trace-link" href={traceHref} target="_blank" rel="noreferrer">
          {hasLangfuseTrace ? "Langfuse trace URL" : "Trace written to: latest_trace.json"}
        </a>
      </div>
    </section>
  );
}
