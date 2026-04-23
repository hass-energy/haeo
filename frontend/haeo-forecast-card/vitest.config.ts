import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.ts", "src/**/*.tsx"],
      exclude: [
        "src/index.ts",
        "src/custom-elements.d.ts",
        "src/types.ts",
        "src/**/*.stories.tsx",
        "src/fixtures/**",
        "src/components/ResponsiveStoryFrame.tsx",
      ],
      thresholds: {
        lines: 85,
        functions: 90,
        branches: 78,
        statements: 85,
      },
    },
  },
});
