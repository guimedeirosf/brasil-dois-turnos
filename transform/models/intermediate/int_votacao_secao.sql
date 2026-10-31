-- Votacao por secao deduplicada pela chave natural (descartes em int_auditoria_descartes).
with ordenado as (
    select
        *,
        row_number() over (
            partition by ano, cd_cargo, turno, uf, cod_municipio_tse, zona, secao, nr_votavel
            order by carregado_em desc, votos desc
        ) as ordem
    from {{ ref('stg_tse__votacao_secao') }}
)

select * exclude (ordem)
from ordenado
where ordem = 1
