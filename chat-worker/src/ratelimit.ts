// Contadores no Workers KV. O IP nunca e gravado: so um hash dele, que expira com o contador.
// KV nao e atomico; para este uso (limite gentil, nao de seguranca) isso basta.

export interface Limites {
  porHora: number;
  porDia: number;
  tetoDiarioLLM: number;
}

export type Veredito = { ok: true } | { ok: false; motivo: "hora" | "dia" | "global" };

async function hash(texto: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

async function ler(kv: KVNamespace, chave: string): Promise<number> {
  return Number((await kv.get(chave)) ?? "0");
}

function carimbos(agora: Date): { hora: string; dia: string } {
  const iso = agora.toISOString();
  return { hora: iso.slice(0, 13), dia: iso.slice(0, 10) };
}

/** Confere e, se couber, consome uma pergunta do IP. */
export async function consumirPergunta(
  kv: KVNamespace,
  ip: string,
  limites: Limites,
  sal: string,
  agora = new Date(),
): Promise<Veredito> {
  const id = await hash(`${sal}:${ip}`);
  const { hora, dia } = carimbos(agora);
  const chaveHora = `h:${id}:${hora}`;
  const chaveDia = `d:${id}:${dia}`;
  const [nHora, nDia, nGlobal] = await Promise.all([
    ler(kv, chaveHora),
    ler(kv, chaveDia),
    ler(kv, `g:${dia}`),
  ]);
  if (nGlobal >= limites.tetoDiarioLLM) return { ok: false, motivo: "global" };
  if (nHora >= limites.porHora) return { ok: false, motivo: "hora" };
  if (nDia >= limites.porDia) return { ok: false, motivo: "dia" };
  await Promise.all([
    kv.put(chaveHora, String(nHora + 1), { expirationTtl: 3600 }),
    kv.put(chaveDia, String(nDia + 1), { expirationTtl: 86400 }),
  ]);
  return { ok: true };
}

/** Conta uma chamada a LLM no teto global do dia. */
export async function contarChamadaLLM(kv: KVNamespace, agora = new Date()): Promise<void> {
  const chave = `g:${carimbos(agora).dia}`;
  await kv.put(chave, String((await ler(kv, chave)) + 1), { expirationTtl: 2 * 86400 });
}
