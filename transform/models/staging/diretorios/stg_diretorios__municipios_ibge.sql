with origem as (
    select * from {{ source('diretorios', 'municipios_ibge') }}
)

select
    cast(id as integer) as cod_municipio_ibge,
    nome as nome_municipio,
    {{ normalizar_texto('nome') }} as nome_municipio_normalizado,
    upper(coalesce(
        microrregiao__mesorregiao__uf__sigla,
        "regiao-imediata__regiao-intermediaria__UF__sigla"
    )) as uf
from origem
