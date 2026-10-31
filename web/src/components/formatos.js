// Formatacao pt-BR e rotulos das categorias de voto.
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const umaCasa = new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const compacto = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

export const num = (v) => (v == null ? "-" : inteiro.format(Number(v)));
export const pct = (v) => (v == null ? "-" : umaCasa.format(Number(v)));
export const curto = (v) => (v == null ? "-" : compacto.format(Number(v)));
export const pp = (v) => (v == null ? "-" : `${Number(v) >= 0 ? "+" : ""}${(Number(v) * 100).toFixed(1).replace(".", ",")} p.p.`);
export const data = (v) => (v == null ? "-" : new Date(v).toLocaleDateString("pt-BR", { timeZone: "UTC" }));

export const ORIGENS = ["CAND_A", "CAND_B", "ESQ", "CENTRO", "DIR", "BRANCO", "NULO", "ABST"];
export const DESTINOS = ["CAND_A", "CAND_B", "BRANCO", "NULO", "ABST"];

export function rotulos(nomeA = "Finalista A", nomeB = "Finalista B") {
  return {
    CAND_A: nomeA,
    CAND_B: nomeB,
    ESQ: "Outros de esquerda",
    CENTRO: "Outros de centro",
    DIR: "Outros de direita",
    BRANCO: "Branco",
    NULO: "Nulo",
    ABST: "Abstencao",
  };
}

export const CORES = {
  CAND_A: "var(--cand-a)",
  CAND_B: "var(--cand-b)",
  ESQ: "var(--esq)",
  CENTRO: "var(--centro)",
  DIR: "var(--dir)",
  BRANCO: "var(--branco)",
  NULO: "var(--nulo)",
  ABST: "var(--abst)",
};

export const UFS = [
  "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
  "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "ZZ",
];
