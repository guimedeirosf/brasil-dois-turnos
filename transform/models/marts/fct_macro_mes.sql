-- Indicadores macro por mes (Brasil). Informalidade e divida externa entram na fase 4.
select
    data_referencia as ano_mes,
    max(valor) filter (where serie = 'pib_mensal_corrente') as pib_mensal_corrente,
    max(valor) filter (where serie = 'desocupacao_pnad') as desocupacao,
    max(valor) filter (where serie = 'dlsp_pct_pib') as divida_liquida_pct_pib,
    max(valor) filter (where serie = 'dbgg_pct_pib') as divida_bruta_pct_pib,
    max(valor) filter (where serie = 'selic_mes_anualizada') as selic,
    max(valor) filter (where serie = 'ipca_var_mensal') as ipca,
    max(valor) filter (where serie = 'cambio_venda_media_mes') as cambio
from {{ ref('stg_bcb__series') }}
group by 1
