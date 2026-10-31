with datas as (
    select
        ano,
        cargo,
        sg_ue,
        min(data_eleicao) filter (where turno = 1) as data_1t,
        min(data_eleicao) filter (where turno = 2) as data_2t
    from {{ ref('int_detalhe_secao') }}
    group by all
)

select
    {{ dbt_utils.generate_surrogate_key(['c.ano', 'c.cargo', 'c.abrangencia']) }} as sk_eleicao,
    c.ano,
    c.cargo,
    c.cd_cargo,
    c.abrangencia,
    c.tem_2t,
    c.nivel_minimo as granularidade_disponivel,
    d.data_1t,
    d.data_2t,
    d.data_1t is not null as carregada
from {{ ref('eleicoes_catalogo') }} as c
left join datas as d
    on
        c.ano = d.ano
        and c.cargo = d.cargo
        and c.abrangencia = d.sg_ue
