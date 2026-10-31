---
title: Historico
---

# Historico

```js
import { consultar } from "./lib/duckdb.js";
import { pct } from "./components/formatos.js";

const resultados = await consultar(
  `select ano, turno, nome_cand_a, nome_cand_b, pct_validos_cand_a, pct_validos_cand_b, pct_abstencao
   from srv_resumo_eleicao where cargo = 'presidente' and abrangencia = 'BR' order by ano, turno`,
);
const macro = await consultar(`select * from fct_macro_mes order by ano_mes`);
```

## Eleicoes presidenciais com 2o turno

```js
display(
  Inputs.table(resultados, {
    format: { ano: String, pct_validos_cand_a: pct, pct_validos_cand_b: pct, pct_abstencao: pct },
    header: {
      ano: "Ano", turno: "Turno", nome_cand_a: "Finalista A", nome_cand_b: "Finalista B",
      pct_validos_cand_a: "A (% validos)", pct_validos_cand_b: "B (% validos)", pct_abstencao: "Abstencao",
    },
  }),
);
```

## Macroeconomia

```js
const serie = view(
  Inputs.select(
    new Map([
      ["Selic (% a.a.)", "selic"],
      ["IPCA (% no mes)", "ipca"],
      ["Desocupacao (%)", "desocupacao"],
      ["Divida liquida do setor publico (% do PIB)", "divida_liquida_pct_pib"],
      ["Divida bruta do governo geral (% do PIB)", "divida_bruta_pct_pib"],
      ["Cambio (R$/US$)", "cambio"],
    ]),
    { label: "Indicador" },
  ),
);
```

```js
const datasEleicao = [...new Set(resultados.map((r) => r.ano))].map((a) => new Date(Date.UTC(a, 9, 1)));
display(
  resize((width) =>
    Plot.plot({
      width,
      height: 320,
      x: { type: "utc", label: null },
      y: { grid: true, label: null },
      marks: [
        Plot.ruleX(datasEleicao, { stroke: "var(--theme-foreground-faint)", strokeDasharray: "3,3" }),
        Plot.lineY(macro.filter((d) => d[serie] != null), { x: (d) => new Date(d.ano_mes), y: serie, stroke: "var(--theme-foreground-focus)", tip: true }),
      ],
    }),
  ),
);
```

<p class="legenda">Linhas tracejadas: meses de eleicao presidencial. Fonte: Banco Central (SGS). Eleicoes de 2002 a 2022 entram na fase 4; o cruzamento com o desempenho do candidato da situacao vem junto.</p>
