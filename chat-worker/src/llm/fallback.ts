import { ErroTransitorio, type LLMProvider } from "./provedor";

export class SemProvedor extends Error {}

/** Tenta os provedores em ordem; troca so em falha transitoria (429, 5xx, timeout). */
export class ComReserva implements LLMProvider {
  readonly nome = "com-reserva";
  ultimoUsado = "";

  constructor(private readonly provedores: LLMProvider[]) {}

  private async tentar(chamada: (p: LLMProvider) => Promise<string>): Promise<string> {
    const falhas: string[] = [];
    for (const provedor of this.provedores) {
      try {
        const texto = await chamada(provedor);
        this.ultimoUsado = provedor.nome;
        return texto;
      } catch (e) {
        if (!(e instanceof ErroTransitorio)) throw e;
        falhas.push(`${provedor.nome}: ${e.message}`);
      }
    }
    throw new SemProvedor(`todos os provedores falharam (${falhas.join("; ")})`);
  }

  generateSQL(sistema: string, pergunta: string): Promise<string> {
    return this.tentar((p) => p.generateSQL(sistema, pergunta));
  }

  summarize(sistema: string, conteudo: string): Promise<string> {
    return this.tentar((p) => p.summarize(sistema, conteudo));
  }
}
