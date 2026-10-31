{# Severidade que so bloqueia em producao (usado nos portoes de publicacao). #}
{% macro severidade_prod() -%}
    {{ 'error' if target.name == 'prod' else 'warn' }}
{%- endmacro %}
