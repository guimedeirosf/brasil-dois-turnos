-- Todo partido com voto tem nota ideologica e faixa.
select distinct
    v.ano,
    v.cargo,
    v.sigla_partido
from {{ ref('int_votacao_secao_categorizada') }} as v
where
    v.nr_votavel not in (95, 96, 97)
    and v.categoria = 'SEM_CLASSIFICACAO'
