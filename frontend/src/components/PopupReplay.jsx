import React from "react";

import ControlBar from "./ControlBar.jsx";
import GridPanel from "./GridPanel.jsx";
import ReplayPanel from "./ReplayPanel.jsx";
import { useReplay } from "../hooks/useReplay.js";

export default function PopupReplay({ data }) {
  const replay = useReplay(data.frames);

  return (
    <section className="replay-modal replay-inline" role="region" aria-label="Replay session">
      <header className="modal-header">
        <div>
          <p className="eyebrow">Memory Playback</p>
          <h2>Replay Session</h2>
          <p className="modal-copy">Dungeon Agent Observability Lab</p>
          <p className="modal-copy modal-copy-strong">Replay debugger for multi-agent behavior</p>
          <p className="modal-copy">
            A cinematic debugging surface for grid-world reasoning, step-by-step decisions, and
            belief drift.
          </p>
          <p className="modal-hint">{data.frames.length} actions loaded from latest trace</p>
        </div>
      </header>

      <ControlBar
        currentIndex={replay.currentIndex}
        frameCount={data.frames.length}
        isPlaying={replay.isPlaying}
        onTimelineChange={replay.jumpTo}
        onPlayPause={replay.togglePlay}
        onRestart={replay.restart}
        onSpeedChange={replay.setSpeed}
        onStepBack={replay.stepBack}
        onStepForward={replay.stepForward}
        speed={replay.speed}
      />

      {replay.currentFrame.highlights.length ? (
        <div className="highlight-banner">
          {replay.currentFrame.highlights.map((highlight) => (
            <span key={highlight.text} className={`highlight-pill ${highlight.level}`}>
              <strong>{highlight.title}</strong> {highlight.text}
            </span>
          ))}
        </div>
      ) : null}

      <div className="replay-layout">
        <GridPanel frame={replay.currentFrame} replayMetadata={data.replayMetadata} />
        <ReplayPanel
          currentFrame={replay.currentFrame}
          frames={data.frames}
          onJumpToFrame={replay.jumpTo}
          replayMetadata={data.replayMetadata}
          traceHref={data.traceHref}
          hasLangfuseTrace={data.hasLangfuseTrace}
        />
      </div>
    </section>
  );
}
