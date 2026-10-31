import { normalizarPergunta, versaoCatalogo } from "./semantica";

export interface RespostaSQL {
  sql: string;
  provedor: string;
}

async function chave(pergunta: string): Promise<string> {
  const texto = `${versaoCatalogo}:${normalizarPergunta(pergunta)}`;
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return "sql:" + [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function lerCache(kv: KVNamespace, pergunta: string): Promise<RespostaSQL | null> {
  return kv.get<RespostaSQL>(await chave(pergunta), "json");
}

export async function gravarCache(
  kv: KVNamespace,
  pergunta: string,
  resposta: RespostaSQL,
  dias: number,
): Promise<void> {
  await kv.put(await chave(pergunta), JSON.stringify(resposta), { expirationTtl: dias * 86400 });
}
