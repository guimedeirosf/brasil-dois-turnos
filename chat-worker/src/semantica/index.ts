import dados from "./semantica.json";

export interface Exemplo {
  pergunta: string;
  sql: string;
}

export const versaoCatalogo: string = dados.versao;
export const exemplos: Exemplo[] = dados.exemplos;

/** Tabela -> colunas permitidas no SQL gerado. */
export const tabelasPermitidas: Map<string, Set<string>> = new Map(
  Object.entries(dados.tabelas as Record<string, string[]>).map(([t, cols]) => [t, new Set(cols)]),
);

const PALAVRAS_VAZIAS = new Set(
  "a o as os de da do das dos e em no na nos nas um uma por para com qual quais quanto quantos como que foi foram"
    .split(" "),
);

function termos(texto: string): Set<string> {
  return new Set(
    texto
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((t) => t.length > 1 && !PALAVRAS_VAZIAS.has(t)),
  );
}

/** Exemplos mais parecidos com a pergunta (sobreposicao de termos, Jaccard). */
export function exemplosParecidos(pergunta: string, k = 6): Exemplo[] {
  const alvo = termos(pergunta);
  return exemplos
    .map((ex) => {
      const t = termos(ex.pergunta);
      const comum = [...t].filter((x) => alvo.has(x)).length;
      return { ex, nota: comum / (t.size + alvo.size - comum || 1) };
    })
    .sort((a, b) => b.nota - a.nota)
    .slice(0, k)
    .map((x) => x.ex);
}

export function promptSistema(pergunta: string): string {
  const pares = exemplosParecidos(pergunta)
    .map((ex) => `Pergunta: ${ex.pergunta}\nSQL:\n${ex.sql.trim()}`)
    .join("\n\n");
  return dados.prompt.replace("{{catalogo}}", dados.catalogoTexto).replace("{{exemplos}}", pares);
}

export function normalizarPergunta(pergunta: string): string {
  return [...termos(pergunta)].sort().join(" ");
}
