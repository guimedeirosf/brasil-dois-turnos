-- Cada linha de votacao com a categoria de voto.
-- 95 = branco; 96 = nulo; 97 = anulado/apuracao em separado, somado aos nulos.
-- Finalistas viram CAND_A/CAND_B; os demais do 1o turno caem em ESQ/CENTRO/DIR pela nota do partido.
select
    v.*,
    c.sigla_partido,
    case
        when v.nr_votavel = 95 then 'BRANCO'
        when v.nr_votavel in (96, 97) then 'NULO'
        when f.categoria is not null then f.categoria
        when v.turno = 1 then coalesce(c.faixa_ideologica, 'SEM_CLASSIFICACAO')
        else 'SEM_CLASSIFICACAO'
    end as categoria
from {{ ref('int_votacao_secao') }} as v
left join {{ ref('int_finalistas') }} as f
    on
        v.ano = f.ano
        and v.cd_cargo = f.cd_cargo
        and v.sg_ue = f.sg_ue
        and v.nr_votavel = f.nr_votavel
left join {{ ref('int_candidatos') }} as c
    on
        v.ano = c.ano
        and v.cd_cargo = c.cd_cargo
        and v.sq_candidato = c.sq_candidato
