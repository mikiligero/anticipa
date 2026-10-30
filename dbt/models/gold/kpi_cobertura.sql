-- K3: cobertura reconciliada — % de viajes observados en RT que casan
-- con el GTFS estático tras la reconciliación (umbral objetivo ≥ 95%).
select
    fecha,
    count(*)                                        as viajes_observados,
    count(*) filter (where reconciliado)            as viajes_reconciliados,
    round(count(*) filter (where reconciliado) * 100.0 / count(*), 1) as cobertura_pct
from {{ ref('reconciliacion_viajes') }}
group by fecha
order by fecha desc
