-- Candidatos de cada eleicao com partido resolvido e nota ideologica.
-- A nota e a da sigla na epoca; se a sigla nao foi avaliada, usa a da sigla atual.
-- So o cargo da eleicao (o arquivo do TSE traz tambem os vices).
with candidatos as (
    select c.*
    from {{ ref('stg_tse__candidatos') }} as c
    inner join {{ ref('eleicoes_catalogo') }} as e
        on
            c.ano = e.ano
            and c.cargo = e.cargo
            and c.cd_cargo = e.cd_cargo
    qualify row_number() over (partition by c.ano, c.cd_cargo, c.sq_candidato order by c.turno) = 1
),

com_nota as (
    select
        c.*,
        p.sigla_atual,
        coalesce(i.score, ia.score) as score_ideologico
    from candidatos as c
    left join {{ ref('int_partidos') }} as p on c.sigla_partido = p.sigla
    left join {{ ref('partidos_ideologia') }} as i on c.sigla_partido = i.sigla
    left join {{ ref('partidos_ideologia') }} as ia on p.sigla_atual = ia.sigla
)

select
    ano,
    cargo,
    cd_cargo,
    sg_ue,
    sq_candidato,
    nr_candidato,
    nome_candidato,
    nome_urna,
    nr_partido,
    sigla_partido,
    sigla_atual,
    coligacao,
    composicao_coligacao,
    situacao_candidatura,
    score_ideologico,
    {{ faixa_ideologica('score_ideologico') }} as faixa_ideologica
from com_nota
