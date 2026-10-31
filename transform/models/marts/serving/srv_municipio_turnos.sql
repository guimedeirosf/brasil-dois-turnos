-- Um municipio por linha: vencedor em cada turno, virada, swing e abstencao. Alimenta o mapa.
with por_turno as (
    select
        sk_eleicao,
        ano,
        cargo,
        turno,
        uf,
        cod_municipio_tse,
        cod_municipio_ibge,
        sum(aptos) as aptos,
        sum(abstencao) as abstencao,
        sum(votos_cand_a) as votos_cand_a,
        sum(votos_cand_b) as votos_cand_b,
        sum(votos_total) - sum(brancos) - sum(nulos) as votos_validos
    from {{ ref('fct_secao_resumo') }}
    group by all
),

pivotado as (
    select
        sk_eleicao,
        ano,
        cargo,
        uf,
        cod_municipio_tse,
        cod_municipio_ibge,
        max(aptos) filter (where turno = 1) as aptos_1t,
        max(abstencao / nullif(aptos, 0)) filter (where turno = 1) as pct_abstencao_1t,
        max(abstencao / nullif(aptos, 0)) filter (where turno = 2) as pct_abstencao_2t,
        max(votos_cand_a / nullif(votos_validos, 0)) filter (where turno = 1) as pct_validos_cand_a_1t,
        max(votos_cand_b / nullif(votos_validos, 0)) filter (where turno = 1) as pct_validos_cand_b_1t,
        max(votos_cand_a / nullif(votos_validos, 0)) filter (where turno = 2) as pct_validos_cand_a_2t,
        max(votos_cand_b / nullif(votos_validos, 0)) filter (where turno = 2) as pct_validos_cand_b_2t,
        max(votos_cand_a) filter (where turno = 1) as votos_cand_a_1t,
        max(votos_cand_b) filter (where turno = 1) as votos_cand_b_1t,
        max(votos_cand_a) filter (where turno = 2) as votos_cand_a_2t,
        max(votos_cand_b) filter (where turno = 2) as votos_cand_b_2t
    from por_turno
    group by all
)

select
    p.*,
    m.nome_municipio,
    m.regiao,
    -- No 1o turno o vencedor entre os finalistas (outro candidato pode ter liderado o municipio)
    case when p.votos_cand_a_1t >= p.votos_cand_b_1t then 'CAND_A' else 'CAND_B' end as vencedor_1t,
    case when p.votos_cand_a_2t >= p.votos_cand_b_2t then 'CAND_A' else 'CAND_B' end as vencedor_2t,
    (p.votos_cand_a_1t >= p.votos_cand_b_1t) <> (p.votos_cand_a_2t >= p.votos_cand_b_2t) as virada,
    p.pct_validos_cand_a_2t - p.pct_validos_cand_a_1t as swing_cand_a,
    p.pct_abstencao_2t - p.pct_abstencao_1t as variacao_abstencao
from pivotado as p
left join {{ ref('dim_municipio') }} as m on p.cod_municipio_ibge = m.cod_municipio_ibge
