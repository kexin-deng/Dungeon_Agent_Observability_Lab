import React, { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <section className="hero-card error-card">
          <p className="eyebrow">Replay Error</p>
          <h1>React loaded, but the replay hit an error.</h1>
          <p className="hero-copy">{String(this.state.error.message || this.state.error)}</p>
        </section>
      );
    }

    return this.props.children;
  }
}
