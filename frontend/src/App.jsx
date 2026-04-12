import React, { useEffect, useState } from "react";
import PopupReplay from "./components/PopupReplay.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { parseLogs } from "./utils/parseLogs.js";

export default function App() {
  const [replayData, setReplayData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadReplay() {
      try {
        const response = await fetch("./artifacts/latest_trace.json", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load trace: ${response.status}`);
        }
        const rawTrace = await response.json();
        if (!cancelled) {
          setReplayData(parseLogs(rawTrace));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown replay load error.");
        }
      }
    }

    loadReplay();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ErrorBoundary>
      <main className="app-shell">
        <div className="ambient ambient-left" />
        <div className="ambient ambient-right" />
        {replayData ? (
          <PopupReplay data={replayData} />
        ) : (
          <section className="hero-card">
            <p className="eyebrow">Dungeon Agent Observability Lab</p>
            <h1>Loading replay session</h1>
            <div className="hero-actions">
              <span className="hero-hint">{error || "Loading latest trace..."}</span>
            </div>
          </section>
        )}
      </main>
    </ErrorBoundary>
  );
}
