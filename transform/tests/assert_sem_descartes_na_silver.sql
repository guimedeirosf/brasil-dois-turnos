{{ config(severity='warn') }}
-- Avisa quando a deduplicacao descartou linhas (detalhes em int_auditoria_descartes).
select * from {{ ref('int_auditoria_descartes') }}
