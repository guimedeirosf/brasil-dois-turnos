-- Porte pelas faixas de populacao do IBGE, com a estimativa mais recente disponivel.
with populacao as (
    select
        cod_municipio_ibge,
        populacao,
        ano as ano_populacao
    from {{ ref('stg_sidra__populacao') }}
    where populacao is not null
    qualify row_number() over (partition by cod_municipio_ibge order by ano desc) = 1
)

select
    i.cod_municipio_ibge,
    i.nome_municipio,
    i.uf,
    u.nome_uf,
    u.regiao,
    t.cod_municipio_tse,
    cast(null as double) as area_km2,  -- fase 4: area territorial do IBGE
    coalesce(t.capital, false) as capital,
    p.populacao,
    p.ano_populacao,
    case
        when p.populacao is null then null
        when p.populacao <= 20000 then 'PEQUENO_I'
        when p.populacao <= 50000 then 'PEQUENO_II'
        when p.populacao <= 100000 then 'MEDIO'
        when p.populacao <= 900000 then 'GRANDE'
        else 'METROPOLE'
    end as porte
from {{ ref('stg_diretorios__municipios_ibge') }} as i
left join {{ ref('stg_diretorios__municipios_tse') }} as t on i.cod_municipio_ibge = t.cod_municipio_ibge
left join {{ ref('uf_regiao') }} as u on i.uf = u.uf
left join populacao as p on i.cod_municipio_ibge = p.cod_municipio_ibge
