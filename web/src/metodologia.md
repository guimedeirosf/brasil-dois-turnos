---
title: Metodologia
---

# Metodologia

## Fontes

| Fonte | Uso | Granularidade |
| --- | --- | --- |
| TSE, Dados Abertos | Votacao por secao, detalhe da apuracao (aptos, comparecimento, brancos, nulos) e candidatos | Secao eleitoral |
| IBGE (localidades, SIDRA, malhas) | Municipios, populacao estimada, malha municipal | Municipio |
| Banco Central (SGS) | Selic, IPCA, cambio, divida liquida e bruta, desocupacao | Brasil, mes |
| De-para TSE x IBGE | Ligacao entre o codigo de municipio do TSE e o do IBGE | Municipio |

Os arquivos das fontes sao copiados sem alteracao (camada Bronze), padronizados e conectados (Silver) e organizados em tabelas de fatos e dimensoes (Gold). Todas as etapas tem testes automaticos: por exemplo, em cada secao, votos dos candidatos mais brancos e nulos precisam ser iguais ao comparecimento, e comparecimento mais abstencao igual aos aptos.

## Categorias de voto

No 1o turno, cada eleitor apto de uma secao esta em uma de oito categorias: os dois candidatos que foram ao 2o turno (CAND_A, o mais votado no 1o turno, e CAND_B), os demais candidatos agrupados por faixa ideologica do partido (esquerda, centro, direita), branco, nulo e abstencao. No 2o turno sao cinco: CAND_A, CAND_B, branco, nulo e abstencao.

## Classificacao partidaria

A faixa ideologica dos demais candidatos vem da nota do partido na escala de 0 (esquerda) a 10 (direita) de Bolognesi, Ribeiro e Codato (2023), "A New Ideological Classification of Brazilian Political Parties", *Dados*, 66(2). Faixas usadas: nota menor que 4, esquerda; de 4 a 6, centro; maior que 6, direita. Partidos criados depois do levantamento recebem uma nota provisoria, sinalizada na tabela de partidos. Siglas que mudaram de nome ou se fundiram sao ligadas a sigla atual.

## Inferencia ecologica

O voto e secreto, entao ninguem sabe como cada eleitor votou nos dois turnos. O que se conhece sao os totais de cada secao. A inferencia ecologica estima, a partir de milhares de secoes, a matriz de transicao: que fracao de cada grupo do 1o turno foi para cada opcao do 2o turno.

- Modelo: R x C multinomial-Dirichlet (biblioteca PyEI), estimado por MCMC com 4 cadeias, 2.000 iteracoes de aquecimento e 2.000 amostras, semente fixa.
- Unidade: secao eleitoral, pareada entre os turnos. Secoes sem par, com variacao de aptos acima de 2% ou com menos de 50 aptos sao descartadas; se o descarte passar de 5% dos aptos, a estimativa nao e publicada.
- Estimativa por UF (UFs grandes sao divididas em grupos de municipios) e agregada para o Brasil ponderando pelos eleitores de cada grupo.
- Publicacao so depois de validar: convergencia (R-hat menor que 1,01), linhas que somam 100%, e reconstrucao do resultado do 2o turno por UF com erro menor que 0,5 ponto percentual.

**Limitacoes.** O resultado e uma estimativa com incerteza, mostrada como intervalo de credibilidade de 95%. Ele descreve fluxos do eleitorado como um todo, nao o comportamento de individuos (falacia ecologica). Grupos pequenos, como os demais candidatos de centro, tem intervalos mais largos.

## Chat

As perguntas sao traduzidas em SQL por um modelo de linguagem gratuito, que so pode consultar as tabelas publicas do projeto. O SQL e validado antes de rodar (somente leitura, tabelas e colunas permitidas, com limite de linhas) e executado no seu navegador. A resposta resume apenas os numeros do resultado. O chat recusa pedidos de opiniao, previsao ou recomendacao de voto.

## Licencas

Codigo sob licenca MIT. Os dados seguem as licencas das fontes originais (TSE, IBGE, Banco Central). Codigo e documentacao tecnica dos modelos estao no repositorio do projeto.
