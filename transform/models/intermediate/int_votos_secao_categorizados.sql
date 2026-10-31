-- Votos por secao x turno x categoria (origem no 1o turno, destino no 2o), incluindo abstencao.
with votos as (
    select
        ano,
        cargo,
        cd_cargo,
        sg_ue,
        turno,
        uf,
        cod_municipio_tse,
        zona,
        secao,
        categoria,
        sum(votos) as votos
    from {{ ref('int_votacao_secao_categorizada') }}
    group by all
),

abstencao as (
    select
        ano,
        cargo,
        cd_cargo,
        sg_ue,
        turno,
        uf,
        cod_municipio_tse,
        zona,
        secao,
        'ABST' as categoria,
        cast(abstencoes as hugeint) as votos
    from {{ ref('int_detalhe_secao') }}
)

select * from votos
union all
select * from abstencao
