{#-
  rsi(change_column, partition_by, order_by, periods=14)
  Relative Strength Index — momentum oscillator, 0-100. >70 = overbought,
  <30 = oversold.

  Formula:  RSI = 100 - 100 / (1 + RS),  RS = avg_gain / avg_loss
  where avg_gain/avg_loss are trailing `periods`-row averages of up-moves and
  down-moves. The caller must supply a per-row `change_column` (close - prev_close);
  we split it into gains/losses and average each with window functions.

  Returns NULL when there are no losses in the window (RS undefined) — acceptable
  with sparse history. Usage:
    {{ rsi('daily_change', 'ticker', 'price_date', 14) }}
-#}
{% macro rsi(change_column, partition_by, order_by, periods=14) -%}
    100 - (100 / (1 + {{ safe_divide(
        "avg(case when " ~ change_column ~ " > 0 then " ~ change_column ~ " else 0 end) over (partition by " ~ partition_by ~ " order by " ~ order_by ~ " rows between " ~ (periods - 1) ~ " preceding and current row)",
        "avg(case when " ~ change_column ~ " < 0 then abs(" ~ change_column ~ ") else 0 end) over (partition by " ~ partition_by ~ " order by " ~ order_by ~ " rows between " ~ (periods - 1) ~ " preceding and current row)"
    ) }}))
{%- endmacro %}
