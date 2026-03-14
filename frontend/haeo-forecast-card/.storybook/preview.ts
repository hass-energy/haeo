import type { Preview } from "@storybook/preact";
import { h } from "preact";

import { CARD_STYLES } from "../src/styles";

type ThemeChoice = "auto" | "light" | "dark";

function parseTheme(value: unknown): ThemeChoice {
  return value === "light" || value === "dark" ? value : "auto";
}

const preview: Preview = {
  globalTypes: {
    theme: {
      name: "Theme",
      description: "Story preview theme",
      defaultValue: "auto",
      toolbar: {
        icon: "mirror",
        items: [
          { value: "auto", title: "Auto" },
          { value: "light", title: "Light" },
          { value: "dark", title: "Dark" },
        ],
      },
    },
  },
  parameters: {
    layout: "padded",
    controls: { expanded: true },
  },
  decorators: [
    (Story, context) => {
      const globals = context.globals as Record<string, unknown>;
      const theme = parseTheme(globals["theme"]);
      const resolvedTheme =
        theme === "auto" && globalThis.matchMedia?.("(prefers-color-scheme: dark)")?.matches ? "dark" : theme;
      const appliedTheme = resolvedTheme === "auto" ? "light" : resolvedTheme;
      const wrapperBackground = appliedTheme === "dark" ? "#12151a" : "#f5f7fa";
      if (globalThis.document?.body) {
        globalThis.document.body.style.background = wrapperBackground;
        globalThis.document.body.style.color = appliedTheme === "dark" ? "#e3e8ef" : "#18202a";
      }
      return h(
        "div",
        {
          "data-theme": appliedTheme,
          style: {
            width: "100%",
            maxWidth: "1280px",
            margin: "0 auto",
            padding: "12px",
            background: wrapperBackground,
          },
        },
        [
          h("style", {
            children: `
            :root {
              --card-background-color: #ffffff;
              --divider-color: #d9dde6;
              --primary-color: #1c63e9;
              --primary-text-color: #18202a;
              --secondary-text-color: #5d6878;
            }
            body {
              margin: 0;
            }
            [data-theme='dark'] {
              --card-background-color: #1f232b;
              --divider-color: #414a59;
              --primary-color: #8ab4ff;
              --primary-text-color: #e3e8ef;
              --secondary-text-color: #a8b1c0;
            }
            ha-card {
              display: block;
              border-radius: 12px;
              border: 1px solid var(--divider-color);
              background: var(--card-background-color);
              box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            }
            ${CARD_STYLES}
          `,
          }),
          h(Story, {}),
        ]
      );
    },
  ],
};

export default preview;
