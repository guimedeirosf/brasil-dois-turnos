// Empacota semantic/ (catalogo, exemplos e prompt) num JSON importado pelo Worker.
// Roda antes de testar e de publicar: npm run build:semantic
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

const raiz = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ler = (arquivo) => readFileSync(resolve(raiz, "semantic", arquivo), "utf8");

const catalogoTexto = ler("catalog.yml");
const catalogo = parse(catalogoTexto);
const exemplos = parse(ler("examples.yml")).exemplos;
const prompt = ler("system_prompt.txt");

const tabelas = Object.fromEntries(
  Object.entries(catalogo.tabelas).map(([nome, spec]) => [nome, Object.keys(spec.colunas ?? {})]),
);
const versao = createHash("sha256")
  .update(catalogoTexto + prompt)
  .digest("hex")
  .slice(0, 12);

writeFileSync(
  resolve(raiz, "chat-worker", "src", "semantica", "semantica.json"),
  JSON.stringify({ versao, catalogoTexto, tabelas, exemplos, prompt }, null, 2),
);
console.log(`semantica ${versao}: ${Object.keys(tabelas).length} tabelas, ${exemplos.length} exemplos`);
