import { describe, expect, it } from "vitest";
import { exemplos, exemplosParecidos, promptSistema, tabelasPermitidas } from "../src/semantica";
import { validarSQL } from "../src/sql/validator";

describe("examples.yml", () => {
  it("tem entre 30 e 50 exemplos", () => {
    expect(exemplos.length).toBeGreaterThanOrEqual(30);
    expect(exemplos.length).toBeLessThanOrEqual(50);
  });

  it.each(exemplos.map((e) => [e.pergunta, e.sql]))("passa no validador: %s", (_, sql) => {
    const r = validarSQL(sql, tabelasPermitidas);
    expect(r, JSON.stringify(r)).toMatchObject({ ok: true });
  });
});

describe("montagem do prompt", () => {
  it("escolhe exemplos parecidos com a pergunta", () => {
    const [primeiro] = exemplosParecidos("para onde foram os eleitores de esquerda no 2o turno?");
    expect(primeiro?.sql).toContain("fct_transicao_estimada");
  });

  it("injeta catalogo e exemplos", () => {
    const prompt = promptSistema("abstencao em 2026");
    expect(prompt).not.toContain("{{catalogo}}");
    expect(prompt).not.toContain("{{exemplos}}");
    expect(prompt).toContain("srv_resumo_eleicao");
  });
});
