import { Component } from "preact";
import type { ComponentChildren, JSX } from "preact";

interface ErrorBoundaryProps {
  children: ComponentChildren;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static override getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return { error: error instanceof Error ? error : new Error(String(error)) };
  }

  override componentDidCatch(): void {
    // State already set by getDerivedStateFromError
  }

  override render(): ComponentChildren {
    if (this.state.error) {
      return <ErrorFallback error={this.state.error} onRetry={() => this.setState({ error: null })} />;
    }
    return this.props.children;
  }
}

function ErrorFallback(props: { error: Error; onRetry: () => void }): JSX.Element {
  return (
    <div className="errorFallback">
      <p>Something went wrong rendering the forecast card.</p>
      <pre className="errorMessage">{props.error.message}</pre>
      <button type="button" className="retryButton" onClick={props.onRetry}>
        Retry
      </button>
    </div>
  );
}
