select
    {{ dbt_utils.generate_surrogate_key(['c.ano', 'c.cd_cargo', 'c.sq_candidato']) }} as sk_candidato,
    e.sk_eleicao,
    c.ano,
    c.cargo,
    c.sq_candidato,
    c.nr_candidato,
    c.nome_candidato,
    c.nome_urna,
    p.sk_partido,
    c.sigla_partido,
    c.sigla_atual,
    c.coligacao,
    c.composicao_coligacao,
    c.situacao_candidatura,
    c.score_ideologico,
    c.faixa_ideologica,
    f.categoria as categoria_2t,
    f.votos_1t
from {{ ref('int_candidatos') }} as c
left join {{ ref('dim_eleicao') }} as e
    on
        c.ano = e.ano
        and c.cargo = e.cargo
        and c.sg_ue = e.abrangencia
left join {{ ref('dim_partido') }} as p on c.sigla_partido = p.sigla
left join {{ ref('int_finalistas') }} as f
    on
        c.ano = f.ano
        and c.cd_cargo = f.cd_cargo
        and c.sq_candidato = f.sq_candidato
