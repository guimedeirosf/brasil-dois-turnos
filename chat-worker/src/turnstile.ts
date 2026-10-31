const URL_VERIFICACAO = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

export async function validarTurnstile(token: string, segredo: string, ip: string | null): Promise<boolean> {
  if (!token) return false;
  const corpo = new FormData();
  corpo.append("secret", segredo);
  corpo.append("response", token);
  if (ip) corpo.append("remoteip", ip);
  const resposta = await fetch(URL_VERIFICACAO, { method: "POST", body: corpo });
  if (!resposta.ok) return false;
  const resultado = (await resposta.json()) as { success?: boolean };
  return resultado.success === true;
}
