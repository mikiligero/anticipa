-- Unión de todas las versiones del GTFS estático (trips + routes).
-- Conservar todas las versiones es requisito de la reconciliación H12':
-- el feed RT puede referenciar trip_ids de una versión anterior.
with trips as (
    -- Nota: el GTFS de Renfe no publica direction_id en trips.txt.
    -- trim() en todos los ids: Renfe publica identificadores con padding
    -- de espacios (trip_id y route_id) — causa raíz del desajuste H12'.
    select
        version,
        trim(trip_id)   as trip_id,
        trim(route_id)  as route_id,
        trim(service_id) as service_id,
        trim(trip_headsign) as trip_headsign
    from {{ source('gtfs', 'trips') }}
),

routes as (
    select
        version,
        trim(route_id)          as route_id,
        trim(route_short_name)  as route_short_name,
        -- El long_name viene con relleno interno de espacios: se colapsa
        replace(regexp_replace(trim(route_long_name), '\s+', ' ', 'g'), ' -', ' – ')
                                as route_long_name
    from {{ source('gtfs', 'routes') }}
)

select
    t.version,
    t.trip_id,
    t.route_id,
    t.service_id,
    t.trip_headsign,
    r.route_short_name,
    r.route_long_name
from trips t
left join routes r
    on t.route_id = r.route_id and t.version = r.version
