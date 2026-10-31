-- Os dois candidatos do 2o turno de cada eleicao. CAND_A = mais votado no 1o turno.
with segundo_turno as (
    select distinct
        ano,
        cargo,
        cd_cargo,
        sg_ue,
        nr_votavel,
        sq_candidato
    from {{ ref('int_votacao_secao') }}
    where turno = 2 and nr_votavel not in (95, 96, 97)
),

primeiro_turno as (
    select
        ano,
        cargo,
        cd_cargo,
        sg_ue,
        nr_votavel,
        sum(votos) as votos_1t
    from {{ ref('int_votacao_secao') }}
    where turno = 1
    group by all
),

ordenados as (
    select
        s.ano,
        s.cargo,
        s.cd_cargo,
        s.sg_ue,
        s.nr_votavel,
        s.sq_candidato,
        p.votos_1t,
        row_number() over (
            partition by s.ano, s.cd_cargo, s.sg_ue
            order by p.votos_1t desc, s.nr_votavel asc
        ) as posicao
    from segundo_turno as s
    left join primeiro_turno as p using (ano, cargo, cd_cargo, sg_ue, nr_votavel)
)

select
    ano,
    cargo,
    cd_cargo,
    sg_ue,
    nr_votavel,
    sq_candidato,
    votos_1t,
    case when posicao = 1 then 'CAND_A' else 'CAND_B' end as categoria
from ordenados
