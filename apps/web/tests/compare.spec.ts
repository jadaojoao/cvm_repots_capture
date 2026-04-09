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

test("deep-link com ids reidrata a comparacao", async ({ page }) => {
  await page.goto("/comparar");

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

  const deepLink = page.url();
  await page.goto(deepLink);

  await expect(page.locator("#resultado-comparacao")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("compare-selected-chip")).toHaveCount(2);
});

test("comparacao multipla dispara download do lote Excel", async ({ page }) => {
  await page.goto("/comparar");

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

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /baixar lote excel/i }).click();

  const download = await downloadPromise;
  expect(await download.suggestedFilename()).toBe("comparar_excel_lote.zip");
});

test("ids invalidos mostram fallback controlado", async ({ page }) => {
  await page.goto("/comparar?ids=999999,888888");

  await expect(
    page.getByRole("alert").filter({ hasText: /comparacao indisponivel no estado atual/i }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("link", { name: /abrir diretorio/i })).toBeVisible();
});
