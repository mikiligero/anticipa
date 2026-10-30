-- Puntualidad consumada por línea y día (% de viajes con retraso final ≤ 5 min).
select
    fecha,
    coalesce(linea, 'SIN_LINEA')                    as linea,
    count(*)                                        as viajes,
    count(*) filter (where puntual)                 as viajes_puntuales,
    round(count(*) filter (where puntual) * 100.0 / count(*), 1) as puntualidad_pct,
    round(avg(retraso_final_min), 2)                as retraso_final_medio_min,
    round(quantile_cont(retraso_final_min, 0.90), 2) as retraso_final_p90_min
from {{ ref('llegadas_consumadas') }}
group by fecha, linea
order by fecha desc, linea
