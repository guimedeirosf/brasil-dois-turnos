// Filtros refletidos na URL (?ano=2026&uf=GO) para permitir compartilhar links.

export function lerParametro(nome, padrao) {
  const valor = new URLSearchParams(location.search).get(nome);
  return valor ?? padrao;
}

/** Liga um input do Observable a um parametro da URL (sem recarregar a pagina). */
export function sincronizarComURL(input, nome) {
  input.addEventListener("input", () => {
    const url = new URL(location.href);
    url.searchParams.set(nome, input.value);
    history.replaceState(null, "", url);
  });
  return input;
}
