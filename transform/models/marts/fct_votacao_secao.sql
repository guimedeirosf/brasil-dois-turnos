select
    e.sk_eleicao,
    v.ano,
    v.cargo,
    v.turno,
    v.uf,
    v.cod_municipio_tse,
    m.cod_municipio_ibge,
    v.zona,
    v.secao,
    v.nr_votavel,
    c.sk_candidato,
    v.categoria,
    v.votos,
    d.aptos,
    d.comparecimento
from {{ ref('int_votacao_secao_categorizada') }} as v
inner join {{ ref('dim_eleicao') }} as e
    on
        v.ano = e.ano
        and v.cargo = e.cargo
        and v.sg_ue = e.abrangencia
left join {{ ref('dim_candidato') }} as c
    on
        v.ano = c.ano
        and v.cargo = c.cargo
        and v.sq_candidato = c.sq_candidato
left join {{ ref('stg_diretorios__municipios_tse') }} as m on v.cod_municipio_tse = m.cod_municipio_tse
left join {{ ref('int_detalhe_secao') }} as d
    on
        v.ano = d.ano
        and v.cd_cargo = d.cd_cargo
        and v.turno = d.turno
        and v.cod_municipio_tse = d.cod_municipio_tse
        and v.zona = d.zona
        and v.secao = d.secao
