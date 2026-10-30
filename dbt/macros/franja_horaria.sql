{% macro franja_horaria(hora_col) %}
    -- Franja de 2 horas alineada con el EDA del Sprint 1 (tabla 14).
    -- División entera (//): en DuckDB '/' es división decimal.
    lpad(cast((cast({{ hora_col }} as integer) // 2) * 2 as varchar), 2, '0')
    || '-' ||
    lpad(cast(((cast({{ hora_col }} as integer) // 2) * 2 + 2) % 24 as varchar), 2, '0')
{% endmacro %}
