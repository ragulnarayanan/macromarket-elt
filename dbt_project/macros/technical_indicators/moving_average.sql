{#-
  moving_average(column, partition_by, order_by, window)
  Simple moving average over the trailing `window` rows (inclusive of current).

  Built on a SQL window function:
    AVG(col) OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN N-1 PRECEDING AND CURRENT ROW)
  With <window rows available (e.g. early dates, or our short history for MA-200),
  it averages whatever exists so far — exactly how a trailing MA should behave.

  Usage:  {{ moving_average('close_price', 'ticker', 'price_date', 20) }}
-#}
{% macro moving_average(column, partition_by, order_by, window) -%}
    avg({{ column }}) over (
        partition by {{ partition_by }}
        order by {{ order_by }}
        rows between {{ window - 1 }} preceding and current row
    )
{%- endmacro %}
