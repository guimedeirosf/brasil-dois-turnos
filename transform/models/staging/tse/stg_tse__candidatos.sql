with origem as (
    select * from {{ source('tse', 'consulta_cand') }}
)

select
    cast(ano_eleicao as integer) as ano,
    cast(cargo as varchar) as cargo,
    cast(nr_turno as integer) as turno,
    cast(upper(trim(sg_ue)) as varchar) as sg_ue,
    cast(cd_cargo as integer) as cd_cargo,
    cast(sq_candidato as bigint) as sq_candidato,
    cast(nr_candidato as integer) as nr_candidato,
    cast({{ normalizar_texto('nm_candidato') }} as varchar) as nome_candidato,
    cast({{ normalizar_texto('nm_urna_candidato') }} as varchar) as nome_urna,
    cast(nr_partido as integer) as nr_partido,
    cast({{ normalizar_texto('sg_partido') }} as varchar) as sigla_partido,
    cast({{ normalizar_texto('nm_coligacao') }} as varchar) as coligacao,
    cast({{ normalizar_texto('ds_composicao_coligacao') }} as varchar) as composicao_coligacao,
    cast({{ normalizar_texto('ds_situacao_candidatura') }} as varchar) as situacao_candidatura,
    cast({{ normalizar_texto('ds_sit_tot_turno') }} as varchar) as situacao_turno
from origem
