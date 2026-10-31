with origem as (
    select * from {{ source('ibge_sidra', 'populacao_estimada') }}
)

select
    cast(d1c as integer) as cod_municipio_ibge,
    cast(d3c as integer) as ano,
    try_cast(v as bigint) as populacao
from origem
