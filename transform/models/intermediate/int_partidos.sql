-- Cada sigla historica resolvida para a sigla atual (fusoes, renomeacoes, incorporacoes).
with recursive cadeia (sigla, sigla_atual, data_evento, profundidade) as (
    select
        sigla_origem,
        sigla_destino,
        data_evento,
        1
    from {{ ref('partidos_sucessao') }}
    union all
    select
        c.sigla,
        s.sigla_destino,
        c.data_evento,
        c.profundidade + 1
    from cadeia as c
    inner join {{ ref('partidos_sucessao') }} as s on c.sigla_atual = s.sigla_origem
    where c.profundidade < 10
),

final_da_cadeia as (
    select
        sigla,
        sigla_atual,
        data_evento as extinta_em
    from cadeia
    qualify row_number() over (partition by sigla order by profundidade desc) = 1
),

siglas as (
    select sigla from {{ ref('partidos_ideologia') }}
    union
    select sigla_partido from {{ ref('stg_tse__candidatos') }}
    union
    select sigla_origem from {{ ref('partidos_sucessao') }}
    union
    select sigla_destino from {{ ref('partidos_sucessao') }}
)

select
    s.sigla,
    coalesce(f.sigla_atual, s.sigla) as sigla_atual,
    f.extinta_em
from siglas as s
left join final_da_cadeia as f on s.sigla = f.sigla
