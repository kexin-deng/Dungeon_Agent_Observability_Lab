import React from "react";

export default function ControlBar({
  currentIndex,
  frameCount,
  isPlaying,
  speed,
  onPlayPause,
  onStepBack,
  onStepForward,
  onRestart,
  onSpeedChange,
  onTimelineChange
}) {
  const speeds = [1, 2, 4];

  return (
    <div className="control-shell">
      <div className="control-cluster">
        <button onClick={onPlayPause} type="button">
          {isPlaying ? "⏸ Pause" : "▶ Play"}
        </button>
        <button onClick={onStepBack} type="button">
          ⏮ Step Back
        </button>
        <button onClick={onStepForward} type="button">
          ⏭ Step Forward
        </button>
        <button onClick={onRestart} type="button">
          R Restart
        </button>
      </div>

      <div className="control-cluster">
        <span className="speed-label">Speed</span>
        {speeds.map((candidate) => (
          <button
            key={candidate}
            className={candidate === speed ? "speed-chip active" : "speed-chip"}
            onClick={() => onSpeedChange(candidate)}
            type="button"
          >
            {candidate}x
          </button>
        ))}
      </div>

      <div className="control-status">
        <span>
          Action {currentIndex + 1} / {frameCount}
        </span>
      </div>

      <div className="timeline-row">
        <span className="timeline-label">Step 0</span>
        <input
          aria-label="Replay timeline"
          className="timeline-slider"
          max={Math.max(frameCount - 1, 0)}
          min={0}
          onChange={(event) => onTimelineChange(Number(event.target.value))}
          type="range"
          value={currentIndex}
        />
        <span className="timeline-label">Step {Math.max(frameCount - 1, 0)}</span>
      </div>
    </div>
  );
}
