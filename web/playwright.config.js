import { defineConfig } from "@playwright/test";

// Serve o build estatico (gerado com BASE_PATH=/); a Gold vem das fixtures (data/ci/gold),
// servida pelo proprio teste em tests/paginas.spec.js.
export default defineConfig({
  testDir: "tests",
  timeout: 60_000,
  use: { baseURL: "http://localhost:4173/" },
  webServer: {
    command: "npx http-server dist -p 4173 --silent -c-1",
    url: "http://localhost:4173/",
    reuseExistingServer: true,
  },
});
