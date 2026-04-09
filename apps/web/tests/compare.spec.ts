import { expect, test } from "@playwright/test";

test("fluxo inicial de comparacao entre empresas", async ({ page }) => {
  await page.goto("/comparar");

  await expect(
    page.getByRole("heading", {
      name: /comparacao de empresas/i,
    }),
  ).toBeVisible();

  const quickAddButtons = page
    .getByTestId("compare-quick-add")
    .filter({ hasNotText: /^--$/ });
  await expect(quickAddButtons.first()).toBeVisible({ timeout: 15_000 });

  await quickAddButtons.first().click();
  await expect(page).toHaveURL(/\/comparar\?ids=\d+/i, {
    timeout: 30_000,
  });

  const secondRoundButtons = page
    .getByTestId("compare-quick-add")
    .filter({ hasNotText: /^--$/ });
  await expect(secondRoundButtons.first()).toBeVisible({ timeout: 15_000 });
  await secondRoundButtons.first().click();

  await expect(page).toHaveURL(/\/comparar\?ids=\d+(%2C|,)\d+/i, {
    timeout: 30_000,
  });
  await expect(page.locator("#resultado-comparacao")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("#resultado-comparacao table")).toBeVisible();
});
