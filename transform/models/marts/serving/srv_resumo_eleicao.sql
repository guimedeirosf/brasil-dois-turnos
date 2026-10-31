-- Numeros-chave por eleicao, turno e abrangencia (BR e cada UF). Pequeno, lido pelo site.
with por_uf as (
    select
        sk_eleicao,
        ano,
        cargo,
        turno,
        uf as abrangencia,
        sum(aptos) as aptos,
        sum(comparecimento) as comparecimento,
        sum(abstencao) as abstencao,
        sum(brancos) as brancos,
        sum(nulos) as nulos,
        sum(votos_cand_a) as votos_cand_a,
        sum(votos_cand_b) as votos_cand_b,
        sum(votos_esq) as votos_esq,
        sum(votos_centro) as votos_centro,
        sum(votos_dir) as votos_dir
    from {{ ref('fct_secao_resumo') }}
    group by all
),

com_brasil as (
    select * from por_uf
    union all
    select
        sk_eleicao,
        ano,
        cargo,
        turno,
        'BR' as abrangencia,
        sum(aptos) as aptos,
        sum(comparecimento) as comparecimento,
        sum(abstencao) as abstencao,
        sum(brancos) as brancos,
        sum(nulos) as nulos,
        sum(votos_cand_a) as votos_cand_a,
        sum(votos_cand_b) as votos_cand_b,
        sum(votos_esq) as votos_esq,
        sum(votos_centro) as votos_centro,
        sum(votos_dir) as votos_dir
    from por_uf
    group by all
),

nomes as (
    select
        sk_eleicao,
        max(nome_urna) filter (where categoria_2t = 'CAND_A') as nome_cand_a,
        max(nome_urna) filter (where categoria_2t = 'CAND_B') as nome_cand_b,
        max(sigla_partido) filter (where categoria_2t = 'CAND_A') as partido_cand_a,
        max(sigla_partido) filter (where categoria_2t = 'CAND_B') as partido_cand_b
    from {{ ref('dim_candidato') }}
    group by 1
)

select
    r.*,
    n.nome_cand_a,
    n.nome_cand_b,
    n.partido_cand_a,
    n.partido_cand_b,
    r.comparecimento - r.brancos - r.nulos as votos_validos,
    r.abstencao / nullif(r.aptos, 0) as pct_abstencao,
    r.votos_cand_a / nullif(r.comparecimento - r.brancos - r.nulos, 0) as pct_validos_cand_a,
    r.votos_cand_b / nullif(r.comparecimento - r.brancos - r.nulos, 0) as pct_validos_cand_b
from com_brasil as r
left join nomes as n on r.sk_eleicao = n.sk_eleicao
