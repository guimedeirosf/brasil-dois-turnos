// Uma unica instancia de DuckDB-WASM para o site. Cada tabela da Gold vira uma view sobre os
// Parquet do R2 listados em _manifest.json. As colunas ano e cargo vem do caminho (hive), entao
// filtros por eleicao leem so a particao necessaria, e o DuckDB baixa so as colunas usadas
// (requisicoes HTTP por intervalo de bytes).
import { DuckDBClient } from "npm:@observablehq/duckdb";
import { GOLD_URL } from "./config.js";

let promessa;

export function banco() {
  promessa ??= abrir();
  return promessa;
}

async function abrir() {
  const resposta = await fetch(`${GOLD_URL}/_manifest.json`, { cache: "no-cache" });
  if (!resposta.ok) throw new Error(`manifesto indisponivel (${resposta.status})`);
  const manifesto = await resposta.json();
  const db = await DuckDBClient.of();
  for (const [tabela, info] of Object.entries(manifesto.tabelas)) {
    const urls = info.arquivos.map((a) => `'${GOLD_URL}/${a.caminho}'`).join(", ");
    await db.query(
      `create or replace view ${tabela} as select * from read_parquet([${urls}], ` +
        `hive_partitioning = true, union_by_name = true)`,
    );
  }
  return { db, manifesto };
}

/** Executa uma consulta e devolve um array de objetos simples. */
export async function consultar(sql, params = []) {
  const { db } = await banco();
  return Array.from(await db.query(sql, params), (linha) => ({ ...linha }));
}

/** Eleicoes com dados carregados (para os filtros). */
export async function eleicoesDisponiveis() {
  return consultar(
    "select ano, cargo, data_1t, data_2t from dim_eleicao where carregada and tem_2t order by ano desc",
  );
}
