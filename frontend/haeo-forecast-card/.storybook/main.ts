import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { StorybookConfig } from "@storybook/preact-vite";

const STYLES_CSS = resolve(process.cwd(), "src/styles.css");
const VIRTUAL_ID = "\0styles-as-text";

const config: StorybookConfig = {
  framework: "@storybook/preact-vite",
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-essentials"],
  viteFinal(config) {
    config.plugins ??= [];
    config.plugins.push({
      name: "css-as-text",
      enforce: "pre",
      resolveId(source: string, importer: string | undefined) {
        if (importer && source.endsWith("styles.css") && !source.includes("node_modules")) {
          return VIRTUAL_ID;
        }
      },
      load(id: string) {
        if (id === VIRTUAL_ID) {
          const css = readFileSync(STYLES_CSS, "utf-8");
          return `export default ${JSON.stringify(css)};`;
        }
      },
    });
    return config;
  },
};

export default config;
