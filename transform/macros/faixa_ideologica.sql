{# Faixa (ESQ, CENTRO, DIR) a partir da nota do partido e do seed limites_ideologicos. #}
{% macro faixa_ideologica(score) -%}
    (
        select l.faixa
        from {{ ref('limites_ideologicos') }} as l
        where
            ({{ score }} > l.limite_inferior or (l.inclui_inferior and {{ score }} = l.limite_inferior))
            and ({{ score }} < l.limite_superior or (l.inclui_superior and {{ score }} = l.limite_superior))
    )
{%- endmacro %}
