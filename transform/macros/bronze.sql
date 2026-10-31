{# Leitura de uma tabela da Bronze (Parquet particionado estilo hive). #}
{% macro bronze(caminho) -%}
    read_parquet(
        '{{ env_var("BRONZE_DIR", "../data/bronze") }}/{{ caminho }}',
        hive_partitioning = true,
        union_by_name = true
    )
{%- endmacro %}
