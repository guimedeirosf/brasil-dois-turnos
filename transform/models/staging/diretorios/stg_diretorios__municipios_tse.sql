with origem as (
    select * from {{ source('diretorios', 'municipios_tse') }}
)

select
    cast(codigo_tse as integer) as cod_municipio_tse,
    cast(codigo_ibge as integer) as cod_municipio_ibge,
    upper(trim(uf)) as uf,
    {{ normalizar_texto('nome_municipio') }} as nome_municipio,
    capital = '1' as capital
from origem
