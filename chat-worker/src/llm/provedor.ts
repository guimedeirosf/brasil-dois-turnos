export const TIMEOUT_MS = 15_000;
export const TEMPERATURA_SQL = 0;
export const TEMPERATURA_RESUMO = 0.3;

/** Falha que justifica trocar de provedor: 429, 5xx ou timeout. */
export class ErroTransitorio extends Error {}

export interface LLMProvider {
  readonly nome: string;
  generateSQL(sistema: string, pergunta: string): Promise<string>;
  summarize(sistema: string, conteudo: string): Promise<string>;
}

/** Base comum: cada provedor so implementa `completar`. */
export abstract class ProvedorBase implements LLMProvider {
  abstract readonly nome: string;

  protected abstract completar(sistema: string, usuario: string, temperatura: number): Promise<string>;

  generateSQL(sistema: string, pergunta: string): Promise<string> {
    return this.completar(sistema, pergunta, TEMPERATURA_SQL);
  }

  summarize(sistema: string, conteudo: string): Promise<string> {
    return this.completar(sistema, conteudo, TEMPERATURA_RESUMO);
  }
}

/** fetch com timeout; converte 429/5xx/timeout em ErroTransitorio. */
export async function postarJson(url: string, corpo: unknown, cabecalhos: Record<string, string>): Promise<unknown> {
  let resposta: Response;
  try {
    resposta = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", ...cabecalhos },
      body: JSON.stringify(corpo),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (e) {
    throw new ErroTransitorio(`falha de rede ou timeout: ${(e as Error).message}`);
  }
  if (resposta.status === 429 || resposta.status >= 500) {
    throw new ErroTransitorio(`status ${resposta.status}`);
  }
  if (!resposta.ok) throw new Error(`status ${resposta.status}: ${(await resposta.text()).slice(0, 200)}`);
  return resposta.json();
}
