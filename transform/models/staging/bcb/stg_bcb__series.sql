with origem as (
    select * from {{ source('bcb_sgs', 'series') }}
)

select
    cast(serie as varchar) as serie,
    cast(codigo_sgs as integer) as codigo_sgs,
    cast(strptime(data, '%d/%m/%Y') as date) as data_referencia,
    try_cast(valor as double) as valor
from origem
