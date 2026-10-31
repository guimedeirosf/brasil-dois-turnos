-- SCD2: cada sigla vale de quando surgiu (fusao/renomeacao) ate quando deixou de existir.
with criacao as (
    select
        sigla_destino as sigla,
        min(data_evento) as criada_em
    from {{ ref('partidos_sucessao') }}
    group by 1
)

select
    {{ dbt_utils.generate_surrogate_key(['p.sigla']) }} as sk_partido,
    i.numero,
    p.sigla,
    p.sigla_atual,
    i.score as score_ideologico,
    {{ faixa_ideologica('i.score') }} as faixa_ideologica,
    i.fonte,
    i.ano_classificacao,
    i.status_conferencia,
    coalesce(c.criada_em, date '1900-01-01') as valido_de,
    coalesce(p.extinta_em, date '9999-12-31') as valido_ate
from {{ ref('int_partidos') }} as p
left join {{ ref('partidos_ideologia') }} as i on p.sigla = i.sigla
left join criacao as c on p.sigla = c.sigla
