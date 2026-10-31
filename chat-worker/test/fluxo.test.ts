import { describe, expect, it } from "vitest";
import { gerarSQL } from "../src/index";
import { ComReserva, SemProvedor } from "../src/llm/fallback";
import { ErroTransitorio, type LLMProvider } from "../src/llm/provedor";
import { consumirPergunta } from "../src/ratelimit";

class Roteiro implements LLMProvider {
  chamadas = 0;
  constructor(
    readonly nome: string,
    private readonly respostas: (string | Error)[],
  ) {}
  private proxima(): Promise<string> {
    const r = this.respostas[Math.min(this.chamadas++, this.respostas.length - 1)];
    return r instanceof Error ? Promise.reject(r) : Promise.resolve(r ?? "");
  }
  generateSQL(): Promise<string> {
    return this.proxima();
  }
  summarize(): Promise<string> {
    return this.proxima();
  }
}

class KVFalso {
  dados = new Map<string, string>();
  async get(chave: string): Promise<string | null> {
    return this.dados.get(chave) ?? null;
  }
  async put(chave: string, valor: string): Promise<void> {
    this.dados.set(chave, valor);
  }
}

const nada = async () => {};

describe("gerarSQL", () => {
  it("tenta de novo com o erro quando o primeiro SQL e invalido", async () => {
    const llm = new Roteiro("x", ["select sigla from dim_partido", "select sigla from dim_partido limit 5"]);
    expect(await gerarSQL(llm, "partidos", nada)).toEqual({ sql: "select sigla from dim_partido limit 5" });
    expect(llm.chamadas).toBe(2);
  });

  it("devolve recusa amigavel depois de duas falhas", async () => {
    const llm = new Roteiro("x", ["drop table x"]);
    expect(await gerarSQL(llm, "apague tudo", nada)).toMatchObject({ recusa: expect.any(String) });
    expect(llm.chamadas).toBe(2);
  });

  it("repassa a recusa da LLM para opiniao", async () => {
    const llm = new Roteiro("x", ["RECUSA: pergunta pede opiniao"]);
    expect(await gerarSQL(llm, "quem e melhor?", nada)).toEqual({ recusa: "pergunta pede opiniao" });
  });
});

describe("ComReserva", () => {
  it("troca de provedor em 429/5xx/timeout", async () => {
    const a = new Roteiro("gemini", [new ErroTransitorio("429")]);
    const b = new Roteiro("groq", ["ok"]);
    const llm = new ComReserva([a, b]);
    expect(await llm.generateSQL("s", "p")).toBe("ok");
    expect(llm.ultimoUsado).toBe("groq");
  });

  it("nao troca em erro permanente", async () => {
    const llm = new ComReserva([new Roteiro("a", [new Error("400")]), new Roteiro("b", ["ok"])]);
    await expect(llm.generateSQL("s", "p")).rejects.toThrow("400");
  });

  it("falha quando todos falham", async () => {
    const llm = new ComReserva([new Roteiro("a", [new ErroTransitorio("503")])]);
    await expect(llm.summarize("s", "p")).rejects.toBeInstanceOf(SemProvedor);
  });
});

describe("limite por IP", () => {
  const limites = { porHora: 2, porDia: 3, tetoDiarioLLM: 100 };

  it("bloqueia apos o limite por hora e por dia", async () => {
    const kv = new KVFalso() as unknown as KVNamespace;
    const t0 = new Date("2026-10-30T10:00:00Z");
    expect(await consumirPergunta(kv, "1.2.3.4", limites, "sal", t0)).toEqual({ ok: true });
    expect(await consumirPergunta(kv, "1.2.3.4", limites, "sal", t0)).toEqual({ ok: true });
    expect(await consumirPergunta(kv, "1.2.3.4", limites, "sal", t0)).toEqual({ ok: false, motivo: "hora" });
    const t1 = new Date("2026-10-30T11:00:00Z");
    expect(await consumirPergunta(kv, "1.2.3.4", limites, "sal", t1)).toEqual({ ok: true });
    expect(await consumirPergunta(kv, "1.2.3.4", limites, "sal", t1)).toEqual({ ok: false, motivo: "dia" });
    expect(await consumirPergunta(kv, "5.6.7.8", limites, "sal", t1)).toEqual({ ok: true });
  });

  it("nao grava o IP em claro", async () => {
    const kv = new KVFalso();
    await consumirPergunta(kv as unknown as KVNamespace, "1.2.3.4", limites, "sal");
    expect([...kv.dados.keys()].some((k) => k.includes("1.2.3.4"))).toBe(false);
  });

  it("respeita o teto global diario", async () => {
    const kv = new KVFalso();
    kv.dados.set(`g:${new Date().toISOString().slice(0, 10)}`, "100");
    expect(await consumirPergunta(kv as unknown as KVNamespace, "9.9.9.9", limites, "sal")).toEqual({
      ok: false,
      motivo: "global",
    });
  });
});
