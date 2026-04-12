import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

function setBootStatus(message) {
  const node = document.getElementById("boot-status");
  if (node) {
    node.textContent = message;
  }
}

window.addEventListener("error", (event) => {
  setBootStatus(`Replay UI crashed: ${event.message}`);
});

window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason instanceof Error ? event.reason.message : String(event.reason);
  setBootStatus(`Replay UI rejected: ${reason}`);
});

const rootNode = document.getElementById("root");

if (!rootNode) {
  setBootStatus("Replay UI could not find #root.");
} else {
  ReactDOM.createRoot(rootNode).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  requestAnimationFrame(() => {
    window.__replayMounted = true;
    setBootStatus("React mounted.");
  });
}
