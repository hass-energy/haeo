import { Reaction } from "mobx";
import type { JSX } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";

type Renderable = JSX.Element | null;

function toError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

function useObserver(render: () => Renderable): Renderable {
  const [, setVersion] = useState(0);
  const reactionRef = useRef<Reaction | null>(null);

  if (!reactionRef.current) {
    reactionRef.current = new Reaction("haeo-preact-observer", () => {
      setVersion((version) => version + 1);
    });
  }

  useEffect(() => {
    return () => {
      reactionRef.current?.dispose();
      reactionRef.current = null;
    };
  }, []);

  let output: Renderable = null;
  let thrown: unknown = null;
  reactionRef.current.track(() => {
    try {
      output = render();
    } catch (error) {
      thrown = error;
    }
  });
  if (thrown !== null) {
    throw toError(thrown);
  }
  return output;
}

export function observer<Props>(component: (props: Props) => Renderable): (props: Props) => Renderable {
  return function ObservedComponent(props: Props): Renderable {
    return useObserver(() => component(props));
  };
}
