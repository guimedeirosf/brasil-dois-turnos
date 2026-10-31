---
title: Pergunte aos dados
---

# Pergunte aos dados

Faca uma pergunta sobre as eleicoes. Um modelo de linguagem transforma a pergunta em SQL, o SQL roda **no seu navegador** sobre os dados publicos do projeto, e a resposta usa so os numeros do resultado. O chat nao opina nem faz previsoes.

```js
import { consultar } from "./lib/duckdb.js";
import { CHAT_URL, TURNSTILE_SITE_KEY } from "./lib/config.js";
import { num, pct } from "./components/formatos.js";

await import("https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit");
```

```js
const caixaTurnstile = html`<div></div>`;
const widget = window.turnstile?.render(caixaTurnstile, { sitekey: TURNSTILE_SITE_KEY, size: "flexible" });
const pergunta = view(
  Inputs.text({
    label: "Pergunta",
    placeholder: "Ex.: para onde foram os eleitores de centro no 2o turno de 2026?",
    submit: "Perguntar",
    width: 640,
  }),
);
display(caixaTurnstile);
```

```js
async function postar(rota, corpo) {
  const resposta = await fetch(`${CHAT_URL}${rota}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(corpo),
  });
  const json = await resposta.json();
  if (!resposta.ok) throw new Error(json.erro ?? `erro ${resposta.status}`);
  return json;
}

function graficoAutomatico(linhas) {
  if (linhas.length < 2 || linhas.length > 40) return null;
  const colunas = Object.keys(linhas[0]);
  const categoria = colunas.find((c) => typeof linhas[0][c] === "string");
  const valor = colunas.find((c) => typeof linhas[0][c] === "number" || typeof linhas[0][c] === "bigint");
  if (!categoria || !valor) return null;
  const dados = linhas.map((l) => ({ ...l, [valor]: Number(l[valor]) }));
  return Plot.plot({
    marginLeft: 140,
    x: { grid: true, label: valor },
    y: { label: null },
    marks: [Plot.barX(dados, { y: categoria, x: valor, sort: { y: "-x" }, fill: "var(--theme-foreground-focus)", tip: true })],
  });
}

async function responder(texto) {
  const token = window.turnstile?.getResponse(widget) ?? "";
  const gerado = await postar("/api/sql", { pergunta: texto, token });
  window.turnstile?.reset(widget);
  if (gerado.recusa) return { recusa: gerado.recusa };
  const linhas = (await consultar(gerado.sql)).map((l) =>
    Object.fromEntries(Object.entries(l).map(([k, v]) => [k, typeof v === "bigint" ? Number(v) : v])),
  );
  const { resposta } = await postar("/api/answer", {
    pergunta: texto,
    sql: gerado.sql,
    ticket: gerado.ticket,
    resultado: linhas.slice(0, 200),
  });
  return { sql: gerado.sql, linhas, resposta };
}
```

```js
const saida = pergunta
  ? responder(pergunta).catch((erro) => ({ erro: erro.message }))
  : null;
```

```js
if (saida === null) {
  display(html`<p class="legenda">Exemplos: "Qual foi a abstencao no 2o turno de 2026?", "Quantos municipios tiveram virada?", "Como os eleitores de esquerda se dividiram no 2o turno em Sao Paulo?"</p>`);
} else if (saida.erro) {
  display(html`<p>Nao foi possivel responder: ${saida.erro}</p>`);
} else if (saida.recusa) {
  display(html`<p class="chat-resposta">${saida.recusa}</p>`);
} else {
  const estimativa = /fct_transicao_estimada/.test(saida.sql);
  display(html`<div class="chat-resposta">
    ${estimativa ? html`<span class="selo-estimativa">Estimativa por inferencia ecologica</span>` : ""}
    <p>${saida.resposta}</p>
  </div>`);
  const grafico = graficoAutomatico(saida.linhas);
  if (grafico) display(grafico);
  display(Inputs.table(saida.linhas, { select: false }));
  display(html`<details><summary>SQL usado</summary><pre><code>${saida.sql}</code></pre></details>`);
}
```

<p class="legenda">Limite: 10 perguntas por hora e 30 por dia. Perguntas e SQL sao registrados sem IP para melhorar os exemplos. Veja a <a href="./metodologia#chat">metodologia</a>.</p>
