---
title: Brasil em dois turnos
---

# Brasil em dois turnos

Como o eleitorado se move entre o 1o e o 2o turno das eleicoes presidenciais, com dados abertos do TSE, do IBGE e do Banco Central.

```js
import { consultar, eleicoesDisponiveis } from "./lib/duckdb.js";
import { data, num, pct, pp } from "./components/formatos.js";

const eleicoes = await eleicoesDisponiveis();
const ultima = eleicoes[0];
const resumo = await consultar(
  `select * from srv_resumo_eleicao
   where ano = ? and cargo = ? and abrangencia = 'BR' order by turno`,
  [ultima.ano, ultima.cargo],
);
const [t1, t2] = resumo;
```

## ${ultima.ano}: ${t2.nome_cand_a} x ${t2.nome_cand_b}

<div class="grid grid-cols-4">
  <div class="card">
    <h3>${t2.nome_cand_a} no 2o turno</h3>
    <span class="numero-chave" style="color: var(--cand-a)">${pct(t2.pct_validos_cand_a)}</span>
    <div class="legenda">${num(t2.votos_cand_a)} votos; no 1o turno, ${pct(t1.pct_validos_cand_a)}</div>
  </div>
  <div class="card">
    <h3>${t2.nome_cand_b} no 2o turno</h3>
    <span class="numero-chave" style="color: var(--cand-b)">${pct(t2.pct_validos_cand_b)}</span>
    <div class="legenda">${num(t2.votos_cand_b)} votos; no 1o turno, ${pct(t1.pct_validos_cand_b)}</div>
  </div>
  <div class="card">
    <h3>Abstencao</h3>
    <span class="numero-chave">${pct(t2.pct_abstencao)}</span>
    <div class="legenda">${pp(t2.pct_abstencao - t1.pct_abstencao)} em relacao ao 1o turno</div>
  </div>
  <div class="card">
    <h3>Eleitores aptos</h3>
    <span class="numero-chave">${num(t2.aptos)}</span>
    <div class="legenda">1o turno em ${data(ultima.data_1t)}, 2o turno em ${data(ultima.data_2t)}</div>
  </div>
</div>

## Explore

- [Transicao entre turnos](./transicao): para onde foi, em estimativa, quem votou em cada grupo no 1o turno.
- [Mapa](./mapa): vencedor por municipio, viradas, swing e abstencao.
- [Economia](./economia): desempenho entre turnos e perfil dos municipios.
- [Historico](./historico): eleicoes desde 2002 e indicadores macroeconomicos.
- [Pergunte aos dados](./chat): perguntas em linguagem natural, respondidas so com os dados.
- [Metodologia](./metodologia): fontes, classificacao partidaria, inferencia ecologica e limitacoes.

<p class="legenda">CAND_A e CAND_B sao os dois candidatos que foram ao 2o turno; CAND_A e o mais votado no 1o turno. As cores sao neutras e nao representam partidos.</p>
