// Enderecos publicos. Ajuste para o bucket do R2 e o Worker do chat em producao.
// Nos testes (Playwright) os valores sao sobrescritos por window.__BDT_CONFIG__.
const sobrescrita = globalThis.__BDT_CONFIG__ ?? {};

export const GOLD_URL = sobrescrita.GOLD_URL ?? "https://dados.SEU_DOMINIO/gold";
export const CHAT_URL = sobrescrita.CHAT_URL ?? "https://brasil-dois-turnos-chat.SEU_USUARIO.workers.dev";
export const TURNSTILE_SITE_KEY = sobrescrita.TURNSTILE_SITE_KEY ?? "PREENCHER";
