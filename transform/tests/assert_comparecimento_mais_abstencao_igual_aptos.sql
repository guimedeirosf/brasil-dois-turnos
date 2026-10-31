select
    sk_eleicao,
    turno,
    uf,
    cod_municipio_tse,
    zona,
    secao,
    aptos,
    comparecimento,
    abstencao
from {{ ref('fct_secao_resumo') }}
where comparecimento + abstencao <> aptos
