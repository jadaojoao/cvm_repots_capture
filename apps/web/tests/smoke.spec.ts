import { expect, test } from "@playwright/test";

test("fluxo inicial de descoberta por empresa", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: /entre por empresa e vá direto ao histórico que importa/i,
    }),
  ).toBeVisible();

  await page
    .getByRole("searchbox", { name: /buscar empresa/i })
    .fill("petrobras");

  await page.getByRole("button", { name: /buscar empresa/i }).click();

  await expect(page).toHaveURL(/\/empresas\?busca=petrobras/i);
  await expect(
    page.getByRole("heading", { name: /diretório público de empresas/i }),
  ).toBeVisible();

  await expect(page.locator("article").first()).toContainText(/PETROBRAS/i);
  await page.getByRole("link", { name: /ver empresa/i }).first().click();

  await expect(page).toHaveURL(/\/empresas\/\d+/);
  await expect(page.locator("h1").first()).toContainText(/PETROBRAS/i);
});
