---
title: Economia
---

# Economia e voto entre turnos

```js
import { consultar, eleicoesDisponiveis } from "./lib/duckdb.js";
import { lerParametro, sincronizarComURL } from "./components/filtros.js";
import { num, pct, pp } from "./components/formatos.js";

const eleicoes = await eleicoesDisponiveis();
```

```js
const ano = view(
  sincronizarComURL(
    Inputs.select(eleicoes.map((e) => e.ano), { label: "Eleicao", value: Number(lerParametro("ano", eleicoes[0].ano)) }),
    "ano",
  ),
);
```

```js
const dados = await consultar(
  `select s.nome_municipio, s.uf, s.regiao, s.swing_cand_a, s.pct_validos_cand_a_2t, s.pct_abstencao_2t,
          m.populacao, m.porte
   from srv_municipio_turnos s
   join dim_municipio m on m.cod_municipio_ibge = s.cod_municipio_ibge
   where s.ano = ? and s.cargo = 'presidente' and m.populacao is not null`,
  [ano],
);
```

## Swing x tamanho do municipio

Cada ponto e um municipio. Eixo horizontal em escala logaritmica.

```js
display(
  resize((width) =>
    Plot.plot({
      width,
      height: 460,
      x: { type: "log", label: "Populacao estimada", tickFormat: (v) => num(v) },
      y: { label: "Swing de CAND_A (p.p. de validos)", tickFormat: (v) => pp(v) },
      color: { legend: true, label: "Regiao" },
      marks: [
        Plot.ruleY([0]),
        Plot.dot(dados, { x: "populacao", y: "swing_cand_a", fill: "regiao", r: 2, fillOpacity: 0.6, tip: true, channels: { municipio: "nome_municipio", uf: "uf" } }),
        Plot.linearRegressionY(dados, { x: "populacao", y: "swing_cand_a", stroke: "var(--theme-foreground)" }),
      ],
    }),
  ),
);
```

```js
const porPorte = d3.rollups(
  dados,
  (v) => ({ municipios: v.length, swing_medio: d3.mean(v, (d) => d.swing_cand_a), abstencao_media: d3.mean(v, (d) => d.pct_abstencao_2t) }),
  (d) => d.porte,
).map(([porte, v]) => ({ porte, ...v }));
display(
  Inputs.table(porPorte, {
    format: { swing_medio: pp, abstencao_media: pct },
    header: { porte: "Porte", municipios: "Municipios", swing_medio: "Swing medio", abstencao_media: "Abstencao media (2o turno)" },
  }),
);
```

<p class="legenda">Proxima etapa (fase 4): PIB per capita, vinculos CLT e estatutarios, MEI e transferencias de renda por municipio, de RAIS, CAGED, Receita Federal e Portal da Transparencia. Correlacao entre municipios nao indica causa nem descreve o voto de pessoas.</p>
