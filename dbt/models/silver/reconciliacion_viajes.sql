-- Reconciliación de identificadores RT ↔ GTFS estático (iteración H12').
-- Para cada trip_id observado en tiempo real se busca la versión más
-- reciente del GTFS que lo contiene (join tolerante a versiones).
with observados as (
    select distinct fecha, trip_id
    from {{ ref('stg_trip_updates') }}
),

match as (
    select
        o.fecha,
        o.trip_id,
        g.version,
        g.route_id,
        g.route_short_name,
        g.route_long_name,
        row_number() over (
            partition by o.fecha, o.trip_id
            order by g.version desc
        ) as rn
    from observados o
    left join {{ ref('stg_gtfs') }} g
        on o.trip_id = g.trip_id
)

select
    fecha,
    trip_id,
    version                       as gtfs_version,
    route_id,
    route_short_name              as linea,
    route_long_name,
    route_id is not null          as reconciliado
from match
where rn = 1
