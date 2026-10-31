---
title: Transicao entre turnos
---

# Transicao entre turnos

<span class="selo-estimativa">Estimativa por inferencia ecologica</span>

O voto e secreto: ninguem sabe em quem cada eleitor votou. As transicoes abaixo sao **estimativas** feitas a partir dos totais de cada secao eleitoral nos dois turnos, com intervalo de credibilidade de 95%. Elas descrevem fluxos do eleitorado, nao o comportamento de pessoas. [Como e calculado](./metodologia#inferencia-ecologica).

```js
import { consultar, eleicoesDisponiveis } from "./lib/duckdb.js";
import { lerParametro, sincronizarComURL } from "./components/filtros.js";
import { CORES, DESTINOS, ORIGENS, UFS, num, pct, rotulos } from "./components/formatos.js";
import { diagramaTransicao } from "./components/sankey.js";

const eleicoes = await eleicoesDisponiveis();
```

```js
const ano = view(
  sincronizarComURL(
    Inputs.select(eleicoes.map((e) => e.ano), {
      label: "Eleicao",
      value: Number(lerParametro("ano", eleicoes[0].ano)),
    }),
    "ano",
  ),
);
const uf = view(
  sincronizarComURL(
    Inputs.select(["BR", ...UFS], {
      label: "Abrangencia",
      value: lerParametro("uf", "BR"),
      format: (u) => (u === "BR" ? "Brasil" : u === "ZZ" ? "Exterior" : u),
    }),
    "uf",
  ),
);
```

```js
const linhas = await consultar(
  `select * from fct_transicao_estimada
   where ano = ? and cargo = 'presidente' and abrangencia = ?`,
  [ano, uf],
);
const [nomes] = await consultar(
  `select nome_cand_a, nome_cand_b from srv_resumo_eleicao
   where ano = ? and cargo = 'presidente' and turno = 2 and abrangencia = 'BR'`,
  [ano],
);
const r = rotulos(nomes?.nome_cand_a, nomes?.nome_cand_b);
```

```js
linhas.length === 0
  ? html`<p>A estimativa para esta eleicao e abrangencia ainda nao foi publicada.</p>`
  : html`<div class="card">${resize((width) => diagramaTransicao(linhas, r, { width }))}</div>
      <p class="legenda">Passe o mouse sobre um fluxo para ver o percentual estimado e o intervalo de credibilidade.
      Status da validacao: ${linhas[0].status_validacao}.</p>`
```

## Matriz estimada

Cada linha mostra como os eleitores de um grupo do 1o turno se distribuiram no 2o turno (soma 100%). Entre parenteses, o intervalo de credibilidade de 95%.

```js
const matriz = ORIGENS.filter((o) => linhas.some((l) => l.origem === o)).map((origem) => {
  const linha = { origem: r[origem] };
  for (const destino of DESTINOS) {
    const c = linhas.find((l) => l.origem === origem && l.destino === destino);
    linha[r[destino]] = c ? `${pct(c.pct_estimado)} (${pct(c.ic_inferior)} a ${pct(c.ic_superior)})` : "-";
  }
  return linha;
});
display(Inputs.table(matriz, { select: false, layout: "auto" }));
```

```js
display(
  Plot.plot({
    marginLeft: 140,
    x: { label: "Fracao estimada (IC 95%)", percent: true, domain: [0, 100] },
    y: { label: null, domain: ORIGENS.map((o) => r[o]) },
    color: { domain: DESTINOS.map((d) => r[d]), range: DESTINOS.map((d) => CORES[d]), legend: true },
    marks: [
      Plot.ruleY(linhas, {
        y: (d) => r[d.origem],
        x1: "ic_inferior",
        x2: "ic_superior",
        stroke: (d) => r[d.destino],
        dy: (d) => (DESTINOS.indexOf(d.destino) - 2) * 3,
      }),
      Plot.dot(linhas, {
        y: (d) => r[d.origem],
        x: "pct_estimado",
        fill: (d) => r[d.destino],
        dy: (d) => (DESTINOS.indexOf(d.destino) - 2) * 3,
        tip: true,
      }),
    ],
  }),
);
```

```js
const fluxos = linhas.filter((l) => !["ESQ", "CENTRO", "DIR"].includes(l.origem) && l.origem !== l.destino);
const migrantes = fluxos.reduce((s, l) => s + l.votos_estimados, 0);
```

<p class="legenda">Entre eleitores dos finalistas, brancos, nulos e abstencao do 1o turno, cerca de ${num(migrantes)} mudaram de grupo no 2o turno (estimativa).</p>
