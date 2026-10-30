-- K10/K12: distribución del retraso por fecha, línea y franja horaria
-- (réplica de la tabla 14 del EDA del Sprint 1, ahora continua).
select
    fecha,
    coalesce(linea, 'SIN_LINEA')            as linea,
    franja,
    count(*)                                as n_observaciones,
    round(avg(arrival_delay_min), 2)        as retraso_medio_min,
    round(median(arrival_delay_min), 2)     as retraso_mediana_min,
    round(quantile_cont(arrival_delay_min, 0.75), 2) as retraso_p75_min,
    round(quantile_cont(arrival_delay_min, 0.90), 2) as retraso_p90_min,
    round(stddev_samp(arrival_delay_min), 2) as retraso_std_min
from {{ ref('retrasos_observados') }}
group by fecha, linea, franja
order by fecha desc, linea, franja
