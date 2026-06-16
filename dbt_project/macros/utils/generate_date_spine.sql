{#-
  generate_date_spine(start_date, end_date)
  Produces a continuous one-row-per-day table between two dates. Useful for
  aligning sources that don't report every day (e.g. monthly FRED series) onto a
  daily calendar so joins don't drop dates. Thin wrapper over dbt_utils.date_spine.

  Args are SQL date expressions (quoted literals or to_date(...)).
  Usage:
    {{ generate_date_spine("'2026-01-01'", "current_date") }}
-#}
{% macro generate_date_spine(start_date, end_date) -%}
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date=start_date,
        end_date=end_date
    ) }}
{%- endmacro %}
