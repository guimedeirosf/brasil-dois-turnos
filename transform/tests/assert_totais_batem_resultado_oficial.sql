{{ config(severity=severidade_prod()) }}
-- Totais nacionais por votavel = resultado oficial divulgado pelo TSE (seed resultados_oficiais),
-- com tolerancia zero. Em producao, eleicao carregada sem resultado oficial no seed tambem falha.
with calculado as (
    select
        ano,
        cargo,
        turno,
        nr_votavel,
        sum(votos) as votos
    from {{ ref('fct_votacao_secao') }}
    group by all
),

divergencias as (
    select
        o.ano,
        o.cargo,
        o.turno,
        o.nr_votavel,
        o.votos as votos_oficiais,
        c.votos as votos_calculados,
        'divergente' as problema
    from {{ ref('resultados_oficiais') }} as o
    left join calculado as c using (ano, cargo, turno, nr_votavel)
    where c.votos is distinct from o.votos
),

sem_referencia as (
    select distinct
        c.ano,
        c.cargo,
        c.turno,
        cast(null as integer) as nr_votavel,
        cast(null as bigint) as votos_oficiais,
        cast(null as bigint) as votos_calculados,
        'sem_resultado_oficial_no_seed' as problema
    from calculado as c
    left join {{ ref('resultados_oficiais') }} as o using (ano, cargo, turno)
    where o.ano is null
)

select * from divergencias
union all
select * from sem_referencia
