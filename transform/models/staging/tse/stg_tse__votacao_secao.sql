with origem as (
    select * from {{ source('tse', 'votacao_secao') }}
)

select
    cast(ano_eleicao as integer) as ano,
    cast(cargo as varchar) as cargo,
    cast(nr_turno as integer) as turno,
    cast(cd_eleicao as integer) as cd_eleicao,
    cast(strptime(dt_eleicao, '%d/%m/%Y') as date) as data_eleicao,
    cast(upper(trim(sg_uf)) as varchar) as uf,
    cast(upper(trim(sg_ue)) as varchar) as sg_ue,
    cast(cd_municipio as integer) as cod_municipio_tse,
    cast({{ normalizar_texto('nm_municipio') }} as varchar) as nome_municipio,
    cast(nr_zona as integer) as zona,
    cast(nr_secao as integer) as secao,
    cast(cd_cargo as integer) as cd_cargo,
    cast(nr_votavel as integer) as nr_votavel,
    cast({{ normalizar_texto('nm_votavel') }} as varchar) as nome_votavel,
    cast(nullif(sq_candidato, '-1') as bigint) as sq_candidato,
    cast(qt_votos as integer) as votos,
    cast(_carregado_em as timestamp) as carregado_em
from origem
