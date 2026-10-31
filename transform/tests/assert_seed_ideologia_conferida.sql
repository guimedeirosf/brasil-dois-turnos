{{ config(severity=severidade_prod()) }}
-- Portao de publicacao: nenhuma nota ideologica provisoria vai para producao.
-- Conferir cada linha contra Bolognesi, Ribeiro e Codato (2023) e marcar status_conferencia = conferido.
select
    sigla,
    score,
    fonte,
    status_conferencia
from {{ ref('partidos_ideologia') }}
where status_conferencia <> 'conferido'
