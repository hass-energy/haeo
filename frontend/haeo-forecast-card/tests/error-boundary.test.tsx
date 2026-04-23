// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import { render } from "preact";

import { ErrorBoundary } from "../src/components/ErrorBoundary";

function ThrowingComponent(): never {
  throw new Error("test render error");
}

describe("ErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    const container = document.createElement("div");
    render(
      <ErrorBoundary>
        <p>ok</p>
      </ErrorBoundary>,
      container,
    );
    expect(container.textContent).toContain("ok");
  });

  it("renders fallback when a child throws", async () => {
    const container = document.createElement("div");
    try {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>,
        container,
      );
    } catch {
      // Error boundaries in Preact may still throw in some environments
    }
    // Wait for Preact's batched re-render after error boundary setState
    await new Promise((r) => {
      setTimeout(r, 20);
    });
    // Verify the error boundary caught the error and rendered fallback
    expect(container.textContent).toContain("Something went wrong");
    expect(container.textContent).toContain("test render error");
  });

  it("recovers after clicking retry", async () => {
    let shouldThrow = true;
    function MaybeThrow(): preact.JSX.Element {
      if (shouldThrow) {
        throw new Error("boom");
      }
      return <p>recovered</p>;
    }

    const container = document.createElement("div");
    try {
      render(
        <ErrorBoundary>
          <MaybeThrow />
        </ErrorBoundary>,
        container,
      );
    } catch {
      // Expected
    }
    await new Promise((r) => {
      setTimeout(r, 20);
    });
    expect(container.textContent).toContain("Something went wrong");

    shouldThrow = false;
    const retryBtn = container.querySelector<HTMLButtonElement>(".retryButton")!;
    retryBtn.click();
    await new Promise((r) => {
      setTimeout(r, 20);
    });
    expect(container.textContent).toContain("recovered");
  });
});
