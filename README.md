# brasil-dois-turnos

Como o eleitorado brasileiro se move entre o 1o e o 2o turno, cruzado com indicadores socioeconomicos. Custo zero, sem servidor ligado, publicado como site estatico com um chat que responde so com os dados.

Toda transicao de voto e uma **estimativa por inferencia ecologica**, publicada com intervalo de credibilidade de 95%.

## Arquitetura

```text
fontes publicas (TSE, IBGE, BCB)
  -> GitHub Actions: Python (Bronze) -> dbt-duckdb (Silver, Gold) -> PyEI (transicoes)
  -> Cloudflare R2 (Parquet da Gold + _manifest.json)
  -> site Observable Framework no GitHub Pages, consultas com DuckDB-WASM no navegador
  -> chat: Cloudflare Worker gera e valida o SQL com uma LLM gratuita; o SQL roda no navegador
```

| Pasta | Conteudo |
| --- | --- |
| `ingestion/` | Fontes -> Bronze (Parquet bruto, colunas como texto, manifesto de cargas) e exportacao/publicacao da Gold |
| `transform/` | Projeto dbt: staging e intermediate (Silver), marts e serving (Gold), seeds e testes de negocio |
| `models_ml/` | Inferencia ecologica R x C (PyEI), pareamento de secoes, validacoes, agrupamento de municipios |
| `semantic/` | Catalogo, exemplos pergunta -> SQL e prompt do chat |
| `web/` | Site (Observable Framework) |
| `chat-worker/` | Cloudflare Worker do chat (TypeScript) |
| `scripts/` | Validacao dos exemplos do chat e sincronizacao do catalogo |
| `manifest/` | Manifesto das cargas da Bronze (versionado) |

## Rodando localmente

Requisitos: [uv](https://docs.astral.sh/uv/), Python 3.12, Node 20+ (para `web/` e `chat-worker/`).

```bash
make setup                  # venv, pacotes, dbt deps e hooks do pre-commit
make exemplos               # fixtures -> Bronze -> dbt build (ci) -> Gold de teste -> exemplos do chat
make test lint              # pytest, ruff, mypy
make worker                 # testes do validador de SQL e do fluxo do chat
cd web && npm ci && BASE_PATH=/ npm run build && npm test   # site + Playwright
```

Carga real (ambiente `dev`, dados em `data/`):

```bash
.venv/bin/python -m ingestion tse --ano 2026 --cargo presidente --ufs RR AP   # amostra de UFs
make ingest-eleicao ANO=2026 CARGO=presidente                                 # Brasil inteiro
make ingest-macro dbt-eleicao dbt-macro exportar
.venv/bin/python -m models_ml inferir --ano 2026 --cargo presidente --uf RR --entrada data/gold --saida data/inferencia
.venv/bin/python -m models_ml agregar --ano 2026 --cargo presidente --parciais data/inferencia --gold data/gold
```

## Configuracao de producao

Segredos do GitHub (Settings -> Secrets): `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `CLOUDFLARE_API_TOKEN`. Variavel do repositorio: `GOLD_PUBLIC_URL` (URL publica da pasta `gold/` no R2).

Segredos do Worker (`wrangler secret put`): `GEMINI_API_KEY`, `GROQ_API_KEY`, `TURNSTILE_SECRET`. Em `chat-worker/wrangler.toml`, preencha os ids dos namespaces KV e `ORIGEM_PERMITIDA`. Em `web/src/lib/config.js`, preencha `GOLD_URL`, `CHAT_URL` e `TURNSTILE_SITE_KEY`.

CORS do bucket R2: `GET` e `HEAD` so para o dominio do site, expondo `Content-Length`, `Content-Range` e `ETag`.

## Portoes de publicacao

Em producao (`DBT_TARGET=prod`) o dbt falha, e nada e publicado, se:

- algum partido em `transform/seeds/partidos_ideologia.csv` estiver com `status_conferencia` diferente de `conferido`. As notas atuais sao provisorias e precisam ser conferidas contra Bolognesi, Ribeiro e Codato (2023); partidos posteriores ao levantamento estao marcados como `imputacao_provisoria`;
- a eleicao carregada nao tiver o resultado oficial do TSE em `transform/seeds/resultados_oficiais.csv` (ano, cargo, turno, numero, votos), ou os totais divergirem dele.

A inferencia so publica com R-hat < 1,01, linhas somando 1, reconstrucao do 2o turno com erro < 0,5 p.p. e descarte de secoes <= 5% dos aptos. Fidelidade dos finalistas abaixo de 0,85 exige revisao manual (`aceitar_revisao` no workflow).

## Estado

| Fase | Estado |
| --- | --- |
| 0. Fundacao | Estrutura, CI, pre-commit, workflows. Falta criar o bucket R2 e os segredos |
| 1. Eleicoes 2026 | Ingestao TSE (layout 2026 conferido), Silver, Gold e testes prontos; validado com recorte real de Roraima |
| 2. Inferencia 2026 | Codigo e validacoes prontos; execucao real com PyEI pendente |
| 3. Site v1 | Paginas prontas e build validado; falta publicar |
| 4. Historico e economia | BCB e SIDRA prontos; RAIS, CAGED, CNPJ, Tesouro e transferencias por implementar; layouts antigos do TSE por conferir |
| 5. Chat | Worker, validador e camada semantica prontos (32 exemplos validados) |
| 6. Expansao | Governador e prefeito por implementar |

Decisoes em aberto: limites da faixa de centro (`limites_ideologicos.csv`), dominio proprio ou `github.io`, ano mais antigo a incluir.

## Licenca

Codigo sob licenca MIT. Os dados seguem as licencas das fontes originais.
