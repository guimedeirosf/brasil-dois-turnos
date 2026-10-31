-- Uma linha por secao e turno, com os votos por categoria. Entrada da inferencia ecologica.
with categorias as (
    select
        ano,
        cargo,
        cd_cargo,
        sg_ue,
        turno,
        uf,
        cod_municipio_tse,
        zona,
        secao,
        sum(votos) filter (where categoria = 'CAND_A') as votos_cand_a,
        sum(votos) filter (where categoria = 'CAND_B') as votos_cand_b,
        sum(votos) filter (where categoria = 'ESQ') as votos_esq,
        sum(votos) filter (where categoria = 'CENTRO') as votos_centro,
        sum(votos) filter (where categoria = 'DIR') as votos_dir,
        sum(votos) filter (where categoria = 'BRANCO') as votos_brancos,
        sum(votos) filter (where categoria = 'NULO') as votos_nulos,
        sum(votos) filter (where categoria not in ('ABST')) as votos_total
    from {{ ref('int_votos_secao_categorizados') }}
    group by all
)

select
    e.sk_eleicao,
    d.ano,
    d.cargo,
    d.turno,
    d.uf,
    d.cod_municipio_tse,
    m.cod_municipio_ibge,
    d.zona,
    d.secao,
    d.aptos,
    d.comparecimento,
    d.abstencoes as abstencao,
    coalesce(c.votos_brancos, 0) as brancos,
    coalesce(c.votos_nulos, 0) as nulos,
    coalesce(c.votos_cand_a, 0) as votos_cand_a,
    coalesce(c.votos_cand_b, 0) as votos_cand_b,
    coalesce(c.votos_esq, 0) as votos_esq,
    coalesce(c.votos_centro, 0) as votos_centro,
    coalesce(c.votos_dir, 0) as votos_dir,
    coalesce(c.votos_total, 0) as votos_total
from {{ ref('int_detalhe_secao') }} as d
inner join {{ ref('dim_eleicao') }} as e
    on
        d.ano = e.ano
        and d.cargo = e.cargo
        and d.sg_ue = e.abrangencia
left join categorias as c
    on
        d.ano = c.ano
        and d.cd_cargo = c.cd_cargo
        and d.turno = c.turno
        and d.cod_municipio_tse = c.cod_municipio_tse
        and d.zona = c.zona
        and d.secao = c.secao
left join {{ ref('stg_diretorios__municipios_tse') }} as m on d.cod_municipio_tse = m.cod_municipio_tse
