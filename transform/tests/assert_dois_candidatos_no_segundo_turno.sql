-- Toda eleicao carregada com tem_2t = true tem exatamente 2 candidatos no 2o turno.
select
    e.sk_eleicao,
    e.ano,
    e.cargo,
    count(c.categoria_2t) as finalistas
from {{ ref('dim_eleicao') }} as e
left join {{ ref('dim_candidato') }} as c on e.sk_eleicao = c.sk_eleicao
where e.tem_2t and e.carregada
group by all
having count(c.categoria_2t) <> 2
