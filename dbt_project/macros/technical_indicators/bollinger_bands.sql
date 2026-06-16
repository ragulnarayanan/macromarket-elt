{#-
  bollinger_band(column, partition_by, order_by, window=20, num_std=2, bound='upper')
  Bollinger Bands wrap a moving average with +/- N standard deviations, marking
  statistically high/low price zones.

    middle = MA(window)
    upper  = middle + num_std * stddev(window)
    lower  = middle - num_std * stddev(window)

  `bound` selects which line to emit ('upper' | 'lower' | 'middle'). Call it three
  times for the three columns. Usage:
    {{ bollinger_band('close_price', 'ticker', 'price_date', 20, 2, 'upper') }}
-#}
{% macro bollinger_band(column, partition_by, order_by, window=20, num_std=2, bound='upper') -%}
    {%- set ma = moving_average(column, partition_by, order_by, window) -%}
    {%- set sd -%}
        stddev({{ column }}) over (
            partition by {{ partition_by }}
            order by {{ order_by }}
            rows between {{ window - 1 }} preceding and current row
        )
    {%- endset -%}
    {%- if bound == 'middle' -%}
        ({{ ma }})
    {%- elif bound == 'lower' -%}
        ({{ ma }}) - ({{ num_std }} * ({{ sd }}))
    {%- else -%}
        ({{ ma }}) + ({{ num_std }} * ({{ sd }}))
    {%- endif -%}
{%- endmacro %}
