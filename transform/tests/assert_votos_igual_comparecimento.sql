-- Por secao e turno: votos dos candidatos + brancos + nulos = comparecimento.
select
    sk_eleicao,
    turno,
    uf,
    cod_municipio_tse,
    zona,
    secao,
    votos_total,
    comparecimento
from {{ ref('fct_secao_resumo') }}
where abs(votos_total - comparecimento) > {{ var('tolerancia_votos') }}
