---
title: Mapa
---

# Mapa municipal

```js
import * as topojson from "npm:topojson-client";
import { consultar, eleicoesDisponiveis } from "./lib/duckdb.js";
import { lerParametro, sincronizarComURL } from "./components/filtros.js";
import { pct, pp } from "./components/formatos.js";

const eleicoes = await eleicoesDisponiveis();
const malha = FileAttachment("data/municipios.topojson").json();
```

```js
const ano = view(
  sincronizarComURL(
    Inputs.select(eleicoes.map((e) => e.ano), { label: "Eleicao", value: Number(lerParametro("ano", eleicoes[0].ano)) }),
    "ano",
  ),
);
const metrica = view(
  sincronizarComURL(
    Inputs.radio(["vencedor_2t", "vencedor_1t", "virada", "swing_cand_a", "pct_abstencao_2t"], {
      label: "Mostrar",
      value: lerParametro("metrica", "vencedor_2t"),
      format: (m) =>
        ({
          vencedor_2t: "Vencedor no 2o turno",
          vencedor_1t: "Vencedor no 1o turno (entre os finalistas)",
          virada: "Viradas",
          swing_cand_a: "Swing de CAND_A",
          pct_abstencao_2t: "Abstencao no 2o turno",
        })[m],
    }),
    "metrica",
  ),
);
```

```js
const dados = await consultar(
  `select s.*, r.nome_cand_a, r.nome_cand_b
   from srv_municipio_turnos s
   join srv_resumo_eleicao r on r.ano = s.ano and r.cargo = s.cargo and r.turno = 2 and r.abrangencia = 'BR'
   where s.ano = ? and s.cargo = 'presidente' and s.uf <> 'ZZ'`,
  [ano],
);
const porCodigo = new Map(dados.map((d) => [String(d.cod_municipio_ibge), d]));
const objeto = Object.values(malha.objects)[0];
const municipios = topojson.feature(malha, objeto);
const contorno = topojson.mesh(malha, objeto, (a, b) => a !== b);
const nomeA = dados[0]?.nome_cand_a ?? "CAND_A";
const nomeB = dados[0]?.nome_cand_b ?? "CAND_B";
const valor = (f) => porCodigo.get(String(f.properties.codarea))?.[metrica];
```

```js
const cor = {
  vencedor_2t: { type: "ordinal", domain: ["CAND_A", "CAND_B"], range: ["var(--cand-a)", "var(--cand-b)"], tickFormat: (c) => (c === "CAND_A" ? nomeA : nomeB), legend: true },
  vencedor_1t: { type: "ordinal", domain: ["CAND_A", "CAND_B"], range: ["var(--cand-a)", "var(--cand-b)"], tickFormat: (c) => (c === "CAND_A" ? nomeA : nomeB), legend: true },
  virada: { type: "ordinal", domain: [false, true], range: ["var(--theme-foreground-faintest)", "var(--estimativa)"], tickFormat: (v) => (v ? "Virou" : "Manteve"), legend: true },
  swing_cand_a: { type: "diverging", scheme: "PuOr", pivot: 0, tickFormat: (v) => pp(v), legend: true, label: `Swing de ${nomeA} (p.p. de validos)` },
  pct_abstencao_2t: { type: "sequential", scheme: "Greys", tickFormat: (v) => pct(v), legend: true, label: "Abstencao no 2o turno" },
}[metrica];

display(
  resize((width) =>
    Plot.plot({
      width,
      height: Math.min(width, 760),
      projection: { type: "mercator", domain: municipios },
      color: cor,
      marks: [
        Plot.geo(municipios, {
          fill: (f) => valor(f),
          title: (f) => {
            const d = porCodigo.get(String(f.properties.codarea));
            if (!d) return "sem dados";
            return `${d.nome_municipio} (${d.uf})\n1o turno: ${d.vencedor_1t === "CAND_A" ? nomeA : nomeB}\n` +
              `2o turno: ${d.vencedor_2t === "CAND_A" ? nomeA : nomeB} (${pct(d.vencedor_2t === "CAND_A" ? d.pct_validos_cand_a_2t : d.pct_validos_cand_b_2t)})\n` +
              `Swing ${nomeA}: ${pp(d.swing_cand_a)}\nAbstencao 2o turno: ${pct(d.pct_abstencao_2t)}`;
          },
        }),
        Plot.geo(contorno, { stroke: "var(--theme-background)", strokeWidth: 0.15 }),
      ],
    }),
  ),
);
```

<div class="grid grid-cols-3">
  <div class="card"><h3>Municipios com virada</h3><span class="numero-chave">${dados.filter((d) => d.virada).length}</span></div>
  <div class="card"><h3>${nomeA} venceu no 2o turno</h3><span class="numero-chave">${dados.filter((d) => d.vencedor_2t === "CAND_A").length}</span></div>
  <div class="card"><h3>${nomeB} venceu no 2o turno</h3><span class="numero-chave">${dados.filter((d) => d.vencedor_2t === "CAND_B").length}</span></div>
</div>

<p class="legenda">Swing: variacao, em pontos percentuais dos votos validos, de ${nomeA} entre o 1o e o 2o turno. Malha municipal do IBGE, simplificada.</p>
