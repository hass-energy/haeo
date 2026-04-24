import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual",
  outputDir: "./tests/visual/results",
  snapshotDir: "./tests/visual/snapshots",
  snapshotPathTemplate: "{snapshotDir}/{arg}{ext}",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:6006",
    screenshot: "off",
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        deviceScaleFactor: 2,
      },
    },
  ],
  webServer: {
    command: "npx storybook build --quiet && npx http-server storybook-static -p 6006 -s",
    port: 6006,
    reuseExistingServer: process.env["CI"] === undefined,
    timeout: 120_000,
  },
});
