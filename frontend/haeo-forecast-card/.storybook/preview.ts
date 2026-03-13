import type { Preview } from "@storybook/preact";
import { h } from "preact";

import { CARD_STYLES } from "../src/styles";

const preview: Preview = {
  parameters: {
    layout: "padded",
    controls: { expanded: true },
  },
  decorators: [
    (Story) =>
      h("div", { style: { width: "100%", maxWidth: "1280px", margin: "0 auto", padding: "12px" } }, [
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
              background: #f5f7fa;
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
      ]),
  ],
};

export default preview;
