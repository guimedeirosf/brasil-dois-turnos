with origem as (
    select * from {{ source('tse', 'detalhe_votacao_secao') }}
)

select
    cast(ano_eleicao as integer) as ano,
    cast(cargo as varchar) as cargo,
    cast(nr_turno as integer) as turno,
    cast(strptime(dt_eleicao, '%d/%m/%Y') as date) as data_eleicao,
    cast(upper(trim(sg_uf)) as varchar) as uf,
    cast(upper(trim(sg_ue)) as varchar) as sg_ue,
    cast(cd_municipio as integer) as cod_municipio_tse,
    cast(nr_zona as integer) as zona,
    cast(nr_secao as integer) as secao,
    cast(cd_cargo as integer) as cd_cargo,
    cast(qt_aptos as integer) as aptos,
    cast(qt_comparecimento as integer) as comparecimento,
    cast(qt_abstencoes as integer) as abstencoes,
    cast(qt_votos_nominais as integer) as votos_nominais,
    cast(qt_votos_brancos as integer) as votos_brancos,
    cast(qt_votos_nulos as integer) as votos_nulos,
    cast(qt_votos_legenda as integer) as votos_legenda,
    cast(qt_votos_anulados_apu_sep as integer) as votos_anulados_apu_sep,
    cast(upper(strip_accents(st_secao_instalada)) = 'SIM' as boolean) as secao_instalada,
    cast(upper(strip_accents(st_secao_anulada)) = 'SIM' as boolean) as secao_anulada,
    cast({{ normalizar_texto('ds_origem_voto') }} as varchar) as origem_voto
from origem
