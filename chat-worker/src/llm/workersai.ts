import { ErroTransitorio, ProvedorBase, TIMEOUT_MS } from "./provedor";

export interface BindingAI {
  run(modelo: string, entrada: unknown): Promise<unknown>;
}

export class WorkersAI extends ProvedorBase {
  readonly nome = "workers-ai";

  constructor(
    private readonly ai: BindingAI,
    private readonly modelo = "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  ) {
    super();
  }

  protected async completar(sistema: string, usuario: string, temperatura: number): Promise<string> {
    const chamada = this.ai.run(this.modelo, {
      temperature: temperatura,
      messages: [
        { role: "system", content: sistema },
        { role: "user", content: usuario },
      ],
    });
    const limite = new Promise<never>((_, rejeitar) =>
      setTimeout(() => rejeitar(new ErroTransitorio("timeout")), TIMEOUT_MS),
    );
    try {
      const resposta = (await Promise.race([chamada, limite])) as { response?: string };
      return resposta.response ?? "";
    } catch (e) {
      if (e instanceof ErroTransitorio) throw e;
      throw new ErroTransitorio(`workers ai: ${(e as Error).message}`);
    }
  }
}
