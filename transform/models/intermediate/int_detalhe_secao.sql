-- Detalhe da apuracao por secao deduplicado pela chave natural.
with ordenado as (
    select
        *,
        row_number() over (
            partition by ano, cd_cargo, turno, uf, cod_municipio_tse, zona, secao
            order by comparecimento desc
        ) as ordem
    from {{ ref('stg_tse__detalhe_votacao_secao') }}
)

select * exclude (ordem)
from ordenado
where ordem = 1
