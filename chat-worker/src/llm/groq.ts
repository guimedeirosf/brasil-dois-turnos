import { ProvedorBase, postarJson } from "./provedor";

interface RespostaChat {
  choices?: { message?: { content?: string } }[];
}

/** Groq expoe a API no formato OpenAI. */
export class Groq extends ProvedorBase {
  readonly nome = "groq";

  constructor(
    private readonly chave: string,
    private readonly modelo = "llama-3.3-70b-versatile",
  ) {
    super();
  }

  protected async completar(sistema: string, usuario: string, temperatura: number): Promise<string> {
    const resposta = (await postarJson(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        model: this.modelo,
        temperature: temperatura,
        messages: [
          { role: "system", content: sistema },
          { role: "user", content: usuario },
        ],
      },
      { authorization: `Bearer ${this.chave}` },
    )) as RespostaChat;
    return resposta.choices?.[0]?.message?.content ?? "";
  }
}
