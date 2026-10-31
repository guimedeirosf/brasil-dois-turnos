import { ProvedorBase, postarJson } from "./provedor";

interface RespostaGemini {
  candidates?: { content?: { parts?: { text?: string }[] } }[];
}

export class Gemini extends ProvedorBase {
  readonly nome = "gemini";

  constructor(
    private readonly chave: string,
    private readonly modelo = "gemini-2.5-flash",
  ) {
    super();
  }

  protected async completar(sistema: string, usuario: string, temperatura: number): Promise<string> {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${this.modelo}:generateContent`;
    const resposta = (await postarJson(
      url,
      {
        systemInstruction: { parts: [{ text: sistema }] },
        contents: [{ role: "user", parts: [{ text: usuario }] }],
        generationConfig: { temperature: temperatura },
      },
      { "x-goog-api-key": this.chave },
    )) as RespostaGemini;
    return resposta.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
  }
}
