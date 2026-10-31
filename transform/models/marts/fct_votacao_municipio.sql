with votos as (
    select
        sk_eleicao,
        ano,
        cargo,
        turno,
        uf,
        cod_municipio_tse,
        cod_municipio_ibge,
        nr_votavel,
        sk_candidato,
        categoria,
        sum(votos) as votos
    from {{ ref('fct_votacao_secao') }}
    group by all
)

select
    *,
    case
        when categoria in ('BRANCO', 'NULO') then null
        else
            votos / sum(votos) filter (where categoria not in ('BRANCO', 'NULO'))
                over (partition by sk_eleicao, turno, cod_municipio_tse)
    end as pct_validos
from votos
