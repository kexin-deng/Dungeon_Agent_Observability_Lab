import React from "react";

export default function ChatMessage({ frame, isLatest = false }) {
  return (
    <article className={frame.agentId === "A" ? "chat-row agent-a" : "chat-row agent-b"}>
      <div className={isLatest ? "chat-bubble latest" : "chat-bubble"}>
        <div className="chat-header">
          <span className="chat-agent">
            {frame.agentEmoji} {frame.agentName}
          </span>
          <span className="chat-meta">
            Step {frame.step} · {frame.latencyLabel}
          </span>
        </div>

        <p className="chat-thought">"{frame.chatThought}"</p>
        <p className="chat-line action-line">{frame.storyActionLine}</p>
        <p className="chat-line result-line">{frame.storyResultLine}</p>
        <p className="chat-line subtle">{frame.storyBeliefLine}</p>
        {frame.chatMessage ? <p className="chat-line subtle">{frame.storyMessageLine}</p> : null}
      </div>
    </article>
  );
}
