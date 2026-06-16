{#-
  safe_divide(numerator, denominator)
  Returns numerator / denominator, but NULL when denominator is 0 (NULLIF),
  so we never hit a divide-by-zero error. Used everywhere we compute returns,
  ratios, dominance %, etc.
  Usage:  {{ safe_divide('close_price - prev_close', 'prev_close') }}
-#}
{% macro safe_divide(numerator, denominator) -%}
    ({{ numerator }}) / nullif(({{ denominator }}), 0)
{%- endmacro %}
