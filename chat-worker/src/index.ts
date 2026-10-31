// Rotas do chat:
//   POST /api/sql     { pergunta, token }        -> { sql, ticket } | { recusa }
//   POST /api/answer  { pergunta, sql, ticket, resultado } -> { resposta }
// O SQL roda no navegador (DuckDB-WASM); o Worker so gera, valida e resume.

import { gravarCache, lerCache } from "./cache";
import { ComReserva, SemProvedor } from "./llm/fallback";
import { Gemini } from "./llm/gemini";
import { Groq } from "./llm/groq";
import type { LLMProvider } from "./llm/provedor";
import { type BindingAI, WorkersAI } from "./llm/workersai";
import { consumirPergunta, contarChamadaLLM } from "./ratelimit";
import { promptSistema, tabelasPermitidas } from "./semantica";
import { validarSQL } from "./sql/validator";
import { validarTurnstile } from "./turnstile";

export interface Env {
  LIMITES: KVNamespace;
  CACHE: KVNamespace;
  AI: BindingAI;
  GEMINI_API_KEY: string;
  GROQ_API_KEY: string;
  TURNSTILE_SECRET: string;
  ORIGEM_PERMITIDA: string;
  LIMITE_HORA_IP: string;
  LIMITE_DIA_IP: string;
  TETO_DIARIO_LLM: string;
  CACHE_DIAS: string;
}

const MAX_LINHAS_RESULTADO = 200;
const MAX_BYTES_RESULTADO = 64_000;
const VALIDADE_TICKET_MS = 10 * 60_000;

const RECUSA_PADRAO =
  "Nao consegui transformar essa pergunta numa consulta aos dados do projeto. " +
  "Tente perguntar sobre votos, abstencao, transicao entre turnos ou indicadores do catalogo.";

const PROMPT_RESUMO =
  "Voce resume resultados de consultas sobre eleicoes brasileiras. Responda em portugues, em no " +
  "maximo 4 frases, usando somente os numeros do resultado. Percentuais vem em fracao (0 a 1): " +
  "mostre em %. Se houver ic_inferior e ic_superior, diga que e uma estimativa por inferencia " +
  "ecologica e cite o intervalo. Nao opine, nao preveja e nao atribua comportamento a pessoas.";

function cors(env: Env): Record<string, string> {
  return {
    "access-control-allow-origin": env.ORIGEM_PERMITIDA,
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type",
    vary: "origin",
  };
}

function json(env: Env, corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...cors(env) },
  });
}

function registrar(evento: Record<string, unknown>): void {
  // Sem IP e sem dados pessoais: so a pergunta, o SQL, o resultado e a latencia.
  console.log(JSON.stringify({ ...evento, em: new Date().toISOString() }));
}

async function assinar(segredo: string, texto: string): Promise<string> {
  const chave = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(segredo),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const assinatura = await crypto.subtle.sign("HMAC", chave, new TextEncoder().encode(texto));
  return [...new Uint8Array(assinatura)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Ticket curto que autoriza o /api/answer para o SQL que este Worker validou. */
async function emitirTicket(env: Env, sql: string, agora = Date.now()): Promise<string> {
  const expira = agora + VALIDADE_TICKET_MS;
  return `${expira}.${await assinar(env.TURNSTILE_SECRET, `${expira}:${sql}`)}`;
}

async function ticketValido(env: Env, sql: string, ticket: string, agora = Date.now()): Promise<boolean> {
  const [expira, assinatura] = ticket.split(".");
  if (!expira || !assinatura || Number(expira) < agora) return false;
  return (await assinar(env.TURNSTILE_SECRET, `${expira}:${sql}`)) === assinatura;
}

export function criarLLM(env: Env): LLMProvider {
  return new ComReserva([new Gemini(env.GEMINI_API_KEY), new Groq(env.GROQ_API_KEY), new WorkersAI(env.AI)]);
}

export async function gerarSQL(
  llm: LLMProvider,
  pergunta: string,
  aoChamar: () => Promise<void>,
): Promise<{ sql: string } | { recusa: string }> {
  const sistema = promptSistema(pergunta);
  let entrada = pergunta;
  for (let tentativa = 0; tentativa < 2; tentativa++) {
    await aoChamar();
    const saida = (await llm.generateSQL(sistema, entrada)).trim();
    if (saida.toUpperCase().startsWith("RECUSA")) {
      return { recusa: saida.replace(/^RECUSA:\s*/i, "") || RECUSA_PADRAO };
    }
    const validacao = validarSQL(saida, tabelasPermitidas);
    if (validacao.ok) return { sql: validacao.sql };
    entrada = `${pergunta}\n\nSua consulta anterior foi rejeitada: ${validacao.erro}. Corrija.\n${saida}`;
  }
  return { recusa: RECUSA_PADRAO };
}

async function rotaSQL(req: Request, env: Env, llm: LLMProvider): Promise<Response> {
  const inicio = Date.now();
  const corpo = (await req.json().catch(() => ({}))) as { pergunta?: string; token?: string };
  const pergunta = (corpo.pergunta ?? "").trim().slice(0, 500);
  if (!pergunta) return json(env, { erro: "pergunta vazia" }, 400);

  const ip = req.headers.get("cf-connecting-ip");
  if (!(await validarTurnstile(corpo.token ?? "", env.TURNSTILE_SECRET, ip))) {
    return json(env, { erro: "verificacao anti-robo falhou" }, 403);
  }
  const veredito = await consumirPergunta(
    env.LIMITES,
    ip ?? "desconhecido",
    {
      porHora: Number(env.LIMITE_HORA_IP),
      porDia: Number(env.LIMITE_DIA_IP),
      tetoDiarioLLM: Number(env.TETO_DIARIO_LLM),
    },
    env.TURNSTILE_SECRET,
  );
  if (!veredito.ok) {
    const mensagem =
      veredito.motivo === "global"
        ? "O chat atingiu o limite diario gratuito. Os paineis continuam funcionando."
        : "Limite de perguntas atingido. Tente de novo mais tarde.";
    return json(env, { erro: mensagem, motivo: veredito.motivo }, 429);
  }

  const emCache = await lerCache(env.CACHE, pergunta);
  if (emCache) {
    registrar({ rota: "sql", pergunta, sql: emCache.sql, sucesso: true, cache: true, ms: Date.now() - inicio });
    return json(env, { sql: emCache.sql, ticket: await emitirTicket(env, emCache.sql), cache: true });
  }

  try {
    const resultado = await gerarSQL(llm, pergunta, () => contarChamadaLLM(env.LIMITES));
    const provedor = llm instanceof ComReserva ? llm.ultimoUsado : llm.nome;
    registrar({ rota: "sql", pergunta, ...resultado, provedor, sucesso: "sql" in resultado, ms: Date.now() - inicio });
    if ("recusa" in resultado) return json(env, resultado);
    await gravarCache(env.CACHE, pergunta, { sql: resultado.sql, provedor }, Number(env.CACHE_DIAS));
    return json(env, { sql: resultado.sql, ticket: await emitirTicket(env, resultado.sql) });
  } catch (e) {
    registrar({ rota: "sql", pergunta, sucesso: false, erro: (e as Error).message, ms: Date.now() - inicio });
    if (e instanceof SemProvedor) return json(env, { erro: "servico de linguagem indisponivel" }, 503);
    throw e;
  }
}

async function rotaResposta(req: Request, env: Env, llm: LLMProvider): Promise<Response> {
  const inicio = Date.now();
  const bruto = await req.text();
  if (bruto.length > MAX_BYTES_RESULTADO) return json(env, { erro: "resultado grande demais" }, 413);
  const corpo = JSON.parse(bruto || "{}") as {
    pergunta?: string;
    sql?: string;
    ticket?: string;
    resultado?: unknown[];
  };
  const { pergunta = "", sql = "", ticket = "", resultado = [] } = corpo;
  if (!(await ticketValido(env, sql, ticket))) return json(env, { erro: "ticket invalido ou expirado" }, 403);
  if (!Array.isArray(resultado) || resultado.length > MAX_LINHAS_RESULTADO) {
    return json(env, { erro: `resultado deve ter ate ${MAX_LINHAS_RESULTADO} linhas` }, 400);
  }
  if (resultado.length === 0) return json(env, { resposta: "A consulta nao retornou dados." });

  await contarChamadaLLM(env.LIMITES);
  const conteudo = `Pergunta: ${pergunta}\nSQL: ${sql}\nResultado (JSON): ${JSON.stringify(resultado)}`;
  const resposta = (await llm.summarize(PROMPT_RESUMO, conteudo)).trim();
  registrar({ rota: "answer", pergunta, sql, sucesso: true, ms: Date.now() - inicio });
  return json(env, { resposta });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(env) });
    if (req.method !== "POST") return json(env, { erro: "metodo nao permitido" }, 405);
    const llm = criarLLM(env);
    if (url.pathname === "/api/sql") return rotaSQL(req, env, llm);
    if (url.pathname === "/api/answer") return rotaResposta(req, env, llm);
    return json(env, { erro: "rota inexistente" }, 404);
  },
} satisfies ExportedHandler<Env>;
