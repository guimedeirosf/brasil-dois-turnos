import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

const GOLD_LOCAL = resolve(import.meta.dirname, "..", "..", "data", "ci", "gold");
const GOLD_URL = "https://gold.teste/gold";

// Antes de cada pagina: aponta o site para a Gold de fixtures e coleta erros do console.
test.beforeEach(async ({ page }, info) => {
  info.erros = [];
  page.on("console", (m) => m.type() === "error" && info.erros.push(m.text()));
  page.on("pageerror", (e) => info.erros.push(e.message));
  await page.addInitScript((url) => {
    window.__BDT_CONFIG__ = { GOLD_URL: url, CHAT_URL: "https://chat.teste", TURNSTILE_SITE_KEY: "1x00000000000000000000AA" };
  }, GOLD_URL);
  await page.route(`${GOLD_URL}/**`, async (rota) => {
    const caminho = decodeURIComponent(new URL(rota.request().url()).pathname.replace(/^\/gold\//, ""));
    const corpo = await readFile(resolve(GOLD_LOCAL, caminho));
    const intervalo = rota.request().headers()["range"];
    if (intervalo) {
      const [, ini, fim] = /bytes=(\d+)-(\d*)/.exec(intervalo);
      const fatia = corpo.subarray(Number(ini), fim ? Number(fim) + 1 : corpo.length);
      return rota.fulfill({
        status: 206,
        body: fatia,
        headers: {
          "content-range": `bytes ${ini}-${Number(ini) + fatia.length - 1}/${corpo.length}`,
          "accept-ranges": "bytes",
          "access-control-allow-origin": "*",
          "access-control-expose-headers": "Content-Range, Content-Length, ETag",
        },
      });
    }
    return rota.fulfill({
      body: corpo,
      headers: { "accept-ranges": "bytes", "access-control-allow-origin": "*" },
    });
  });
});

test.afterEach(async ({}, info) => {
  expect(info.erros, info.erros.join("\n")).toEqual([]);
});

test("inicio mostra os numeros-chave da ultima eleicao", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByText("Eleitores aptos")).toBeVisible();
  await expect(page.locator(".numero-chave").first()).toContainText("%");
});

test("transicao reflete o filtro na URL", async ({ page }) => {
  await page.goto("./transicao?uf=RR");
  await expect(page.getByText("Estimativa por inferencia ecologica").first()).toBeVisible();
  await page.getByLabel("Abrangencia").selectOption("BR");
  await expect(page).toHaveURL(/uf=BR/);
});

test("mapa renderiza", async ({ page }) => {
  await page.goto("./mapa");
  await expect(page.locator("svg path").first()).toBeVisible({ timeout: 30_000 });
});

for (const pagina of ["economia", "historico", "metodologia"]) {
  test(`${pagina} carrega`, async ({ page }) => {
    await page.goto(`./${pagina}`);
    await expect(page.locator("h1")).toBeVisible();
  });
}
