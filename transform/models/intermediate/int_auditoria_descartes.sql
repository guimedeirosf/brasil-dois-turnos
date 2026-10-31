-- Linhas descartadas na deduplicacao da Silver, por tabela e particao.
with votacao as (
    select
        ano,
        cargo,
        turno,
        uf,
        count(*) - 1 as excedente
    from {{ ref('stg_tse__votacao_secao') }}
    group by ano, cargo, turno, uf, cod_municipio_tse, zona, secao, nr_votavel
    having count(*) > 1
),

detalhe as (
    select
        ano,
        cargo,
        turno,
        uf,
        count(*) - 1 as excedente
    from {{ ref('stg_tse__detalhe_votacao_secao') }}
    group by ano, cargo, turno, uf, cod_municipio_tse, zona, secao
    having count(*) > 1
)

select
    'votacao_secao' as tabela,
    'duplicata_chave_natural' as motivo,
    ano,
    cargo,
    turno,
    uf,
    sum(excedente) as linhas
from votacao
group by all
union all
select
    'detalhe_votacao_secao' as tabela,
    'duplicata_chave_natural' as motivo,
    ano,
    cargo,
    turno,
    uf,
    sum(excedente) as linhas
from detalhe
group by all
