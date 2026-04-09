import { expect, test } from "@playwright/test";

test("fluxo inicial de descoberta por empresa", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: /entre por empresa e va direto ao historico que importa/i,
    }),
  ).toBeVisible();

  await page
    .getByRole("searchbox", { name: /buscar empresa/i })
    .fill("petrobras");

  await page
    .getByRole("searchbox", { name: /buscar empresa/i })
    .press("Enter");

  await expect(page).toHaveURL(/\/empresas\?busca=petrobras/i, {
    timeout: 30_000,
  });
  await expect(
    page.getByRole("heading", { name: /diretorio publico de empresas/i }),
  ).toBeVisible({ timeout: 30_000 });

  await expect(page.locator("article").first()).toContainText(/PETROBRAS/i);
  await page.getByRole("link", { name: /ver empresa/i }).first().click();

  await expect(page).toHaveURL(/\/empresas\/\d+/);
  await expect(page.locator("h1").first()).toContainText(/PETROBRAS/i);
});

test("detalhe da empresa dispara download do Excel", async ({ page }) => {
  await page.goto("/empresas/9512");

  await expect(page.locator("h1").first()).toContainText(/PETROBRAS/i, {
    timeout: 30_000,
  });

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /baixar excel/i }).click();

  const download = await downloadPromise;
  expect(await download.suggestedFilename()).toMatch(/^PETR4(?:\.SA)?_\d{8}\.xlsx$/i);
});
