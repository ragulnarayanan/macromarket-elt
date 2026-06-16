{#-
  generate_schema_name — controls which Snowflake schema a model lands in.

  WHY override the default: dbt's built-in version builds "<target_schema>_<custom>"
  (so +schema: silver would create SILVER_silver). For a clean medallion layout we
  want the custom schema name used AS-IS — so +schema: silver -> SILVER, gold -> GOLD.

  - No +schema set on a model  -> falls back to the profile's default schema.
  - +schema set                -> that exact name (upper-cased for Snowflake).
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}
