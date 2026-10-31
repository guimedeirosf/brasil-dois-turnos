import { Parser } from "node-sql-parser";

export const TAMANHO_MAXIMO = 4000;
export const LIMITE_MAXIMO = 1000;

// O DuckDB nao tem dialeto proprio no parser; o do Postgres cobre o SQL que pedimos a LLM.
const OPCOES = { database: "PostgresQL" } as const;
const parser = new Parser();

const FUNCOES_PROIBIDAS = new Set([
  "glob",
  "parquet_scan",
  "parquet_metadata",
  "parquet_schema",
  "sniff_csv",
  "query",
  "query_table",
  "getenv",
  "current_setting",
  "set_config",
  "install",
  "load",
]);
const PREFIXOS_PROIBIDOS = ["read_", "duckdb_", "pragma_", "pg_", "httpfs", "s3_", "iceberg_", "delta_"];

export type Resultado = { ok: true; sql: string } | { ok: false; erro: string };

type No = Record<string, unknown>;

function ehNo(x: unknown): x is No {
  return typeof x === "object" && x !== null;
}

function texto(valor: unknown): string | undefined {
  if (typeof valor === "string") return valor;
  if (ehNo(valor)) {
    if (typeof valor.value === "string") return valor.value;
    if (ehNo(valor.expr)) return texto(valor.expr);
    if (Array.isArray(valor.name)) return valor.name.map(texto).join(".");
  }
  return undefined;
}

interface Coleta {
  funcoes: Set<string>;
  colunas: Set<string>;
  apelidos: Set<string>;
  ctes: Set<string>;
  tabelas: Set<string>;
}

function percorrer(no: unknown, c: Coleta): void {
  if (Array.isArray(no)) {
    no.forEach((x) => percorrer(x, c));
    return;
  }
  if (!ehNo(no)) return;
  if (no.type === "function" || no.type === "aggr_func") {
    const nome = texto(no.name);
    if (nome) c.funcoes.add(nome.toLowerCase());
  }
  if (no.type === "column_ref") {
    const coluna = texto(no.column);
    if (coluna && coluna !== "*") c.colunas.add(coluna.toLowerCase());
  }
  if (typeof no.as === "string" || ehNo(no.as)) {
    const apelido = texto(no.as);
    if (apelido) c.apelidos.add(apelido.toLowerCase());
  }
  if (Array.isArray(no.with)) {
    for (const cte of no.with) {
      const nome = ehNo(cte) ? texto(cte.name) : undefined;
      if (nome) c.ctes.add(nome.toLowerCase());
    }
  }
  if (Array.isArray(no.from)) {
    for (const f of no.from) {
      if (ehNo(f) && typeof f.table === "string") c.tabelas.add(f.table.toLowerCase());
    }
  }
  Object.values(no).forEach((v) => percorrer(v, c));
}

function valorLimite(ast: No): number | undefined {
  const limite = ast.limit;
  if (!ehNo(limite) || !Array.isArray(limite.value) || limite.value.length === 0) return undefined;
  const ultimo = limite.value[limite.value.length - 1];
  return ehNo(ultimo) && typeof ultimo.value === "number" ? ultimo.value : undefined;
}

/** Valida o SQL gerado pela LLM. Usa a arvore do parser, nunca regex sobre o texto. */
export function validarSQL(sqlBruto: string, permitidas: Map<string, Set<string>>): Resultado {
  const sql = sqlBruto
    .trim()
    .replace(/^```(?:sql)?\s*/i, "")
    .replace(/```$/, "")
    .trim()
    .replace(/;\s*$/, "");
  if (sql.length === 0) return { ok: false, erro: "SQL vazio" };
  if (sql.length > TAMANHO_MAXIMO) return { ok: false, erro: `SQL maior que ${TAMANHO_MAXIMO} caracteres` };

  let arvore: unknown;
  try {
    arvore = parser.astify(sql, OPCOES);
  } catch (e) {
    return { ok: false, erro: `SQL invalido: ${(e as Error).message.slice(0, 200)}` };
  }
  const instrucoes = Array.isArray(arvore) ? arvore : [arvore];
  if (instrucoes.length !== 1) return { ok: false, erro: "apenas uma instrucao e permitida" };
  const ast = instrucoes[0];
  if (!ehNo(ast) || ast.type !== "select") return { ok: false, erro: "apenas SELECT e permitido" };

  const coleta: Coleta = {
    funcoes: new Set(),
    colunas: new Set(),
    apelidos: new Set(),
    ctes: new Set(),
    tabelas: new Set(),
  };
  percorrer(ast, coleta);

  for (const f of coleta.funcoes) {
    if (FUNCOES_PROIBIDAS.has(f) || PREFIXOS_PROIBIDOS.some((p) => f.startsWith(p))) {
      return { ok: false, erro: `funcao nao permitida: ${f}` };
    }
  }

  let tabelasDaLista: string[];
  try {
    tabelasDaLista = parser.tableList(sql, OPCOES).map((t) => t.split("::")[2]?.toLowerCase() ?? "");
  } catch {
    return { ok: false, erro: "nao foi possivel listar as tabelas" };
  }
  const usadas = new Set([...tabelasDaLista, ...coleta.tabelas]);
  for (const t of usadas) {
    if (!permitidas.has(t) && !coleta.ctes.has(t)) return { ok: false, erro: `tabela nao permitida: ${t}` };
  }

  const colunasConhecidas = new Set<string>();
  for (const t of usadas) permitidas.get(t)?.forEach((c) => colunasConhecidas.add(c));
  for (const coluna of coleta.colunas) {
    if (!colunasConhecidas.has(coluna) && !coleta.apelidos.has(coluna)) {
      return { ok: false, erro: `coluna desconhecida: ${coluna}` };
    }
  }

  const limite = valorLimite(ast);
  if (limite === undefined) return { ok: false, erro: "LIMIT obrigatorio" };
  if (limite > LIMITE_MAXIMO) return { ok: false, erro: `LIMIT maximo e ${LIMITE_MAXIMO}` };

  return { ok: true, sql };
}
