{# Maiusculas, sem espacos nas pontas e sem acentos. Usado em toda chave textual da Silver. #}
{% macro normalizar_texto(coluna) -%}
    nullif(upper(trim(strip_accents({{ coluna }}))), '#NULO')
{%- endmacro %}
