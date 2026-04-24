import { expect, test } from "@playwright/test";

const stories = [
  { id: "forecastcard-forecastcardview--default", name: "ForecastCardView-default" },
  { id: "forecastcard-forecastcardview--hovered", name: "ForecastCardView-hovered" },
  { id: "forecastcard-legend--default", name: "Legend-default" },
  { id: "forecastcard-tooltip--default", name: "Tooltip-default" },
  { id: "forecastcard-powerstacklayer--default", name: "PowerStackLayer-default" },
];

for (const story of stories) {
  test(`visual: ${story.name}`, async ({ page }) => {
    await page.goto(`/iframe.html?id=${story.id}&viewMode=story`, {
      waitUntil: "networkidle",
    });
    // Allow MobX reactions and SVG rendering to settle
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot(`${story.name}.png`, {
      maxDiffPixelRatio: 0.01,
    });
  });
}
