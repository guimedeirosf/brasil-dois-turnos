-- Todo municipio da votacao (fora o exterior) tem codigo IBGE e existe em dim_municipio.
select distinct
    f.uf,
    f.cod_municipio_tse,
    f.cod_municipio_ibge
from {{ ref('fct_secao_resumo') }} as f
left join {{ ref('dim_municipio') }} as m on f.cod_municipio_ibge = m.cod_municipio_ibge
where
    f.uf <> 'ZZ'
    and (f.cod_municipio_ibge is null or m.cod_municipio_ibge is null)
