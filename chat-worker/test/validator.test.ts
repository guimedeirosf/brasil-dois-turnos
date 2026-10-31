import { describe, expect, it } from "vitest";
import { tabelasPermitidas } from "../src/semantica";
import { validarSQL } from "../src/sql/validator";

const valida = (sql: string) => validarSQL(sql, tabelasPermitidas);

describe("validarSQL", () => {
  it("aceita SELECT simples com LIMIT", () => {
    const r = valida("select abrangencia, aptos from srv_resumo_eleicao where turno = 2 limit 10");
    expect(r).toEqual({ ok: true, sql: expect.any(String) });
  });

  it("aceita WITH ... SELECT e apelidos no ORDER BY", () => {
    const r = valida(`
      with base as (select uf, count(*) as n from srv_municipio_turnos where virada group by uf)
      select uf, n from base order by n desc limit 5`);
    expect(r.ok).toBe(true);
  });

  it("remove cerca de codigo e ponto e virgula final", () => {
    const r = valida("```sql\nselect turno from srv_resumo_eleicao limit 1;\n```");
    expect(r).toEqual({ ok: true, sql: "select turno from srv_resumo_eleicao limit 1" });
  });

  it.each([
    "insert into dim_partido values (1)",
    "delete from dim_partido",
    "update dim_partido set sigla = 'X'",
    "drop table dim_partido",
    "create table x as select 1",
  ])("bloqueia DML/DDL: %s", (sql) => {
    expect(valida(sql).ok).toBe(false);
  });

  it.each([
    "copy dim_partido to 'x.csv'",
    "attach 'x.db'",
    "install httpfs",
    "load httpfs",
    "pragma version",
    "set memory_limit = '1GB'",
  ])("bloqueia comandos do DuckDB: %s", (sql) => {
    expect(valida(sql).ok).toBe(false);
  });

  it.each([
    "select * from read_csv('https://exemplo.com/x.csv') limit 1",
    "select * from read_parquet('s3://bucket/x.parquet') limit 1",
    "select glob('*') from dim_partido limit 1",
    "select getenv('HOME') from dim_partido limit 1",
    "select * from duckdb_settings() limit 1",
  ])("bloqueia funcoes de arquivo e rede: %s", (sql) => {
    const r = valida(sql);
    expect(r.ok).toBe(false);
  });

  it("bloqueia multiplas instrucoes", () => {
    const r = valida("select 1 from dim_partido limit 1; select 2 from dim_partido limit 1");
    expect(r).toMatchObject({ ok: false });
  });

  it("bloqueia tabela fora da lista", () => {
    expect(valida("select * from information_schema.tables limit 1")).toMatchObject({ ok: false });
    expect(valida("select * from usuarios limit 1")).toMatchObject({
      ok: false,
      erro: expect.stringContaining("usuarios"),
    });
  });

  it("bloqueia coluna inexistente", () => {
    expect(valida("select senha from dim_partido limit 1")).toMatchObject({
      ok: false,
      erro: expect.stringContaining("senha"),
    });
  });

  it("exige LIMIT e no maximo 1000", () => {
    expect(valida("select sigla from dim_partido")).toMatchObject({ erro: "LIMIT obrigatorio" });
    expect(valida("select sigla from dim_partido limit 5000")).toMatchObject({ ok: false });
    expect(valida("select sigla from dim_partido limit 1000").ok).toBe(true);
  });

  it("recusa SQL muito longo", () => {
    const sql = `select sigla from dim_partido where sigla in (${"'X',".repeat(1500)}'Y') limit 1`;
    expect(valida(sql)).toMatchObject({ ok: false, erro: expect.stringContaining("4000") });
  });
});
