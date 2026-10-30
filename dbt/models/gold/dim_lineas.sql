-- Dimensión trip → línea y destino (última versión GTFS por trip_id).
-- La consume el job de streaming para etiquetar el estado en vivo.
-- El destino sale de la ÚLTIMA parada del viaje en stop_times: el
-- trip_headsign de Renfe viene vacío (o "CIVIS", que es un tipo de servicio).
with ultima_parada as (
    select
        version,
        trim(trip_id)                                            as trip_id,
        arg_max(
            trim(cast(stop_id as varchar)),
            cast(trim(cast(stop_sequence as varchar)) as integer)
        )                                                        as last_stop_id
    from {{ source('gtfs', 'stop_times') }}
    group by version, trim(trip_id)
),

destinos as (
    select
        u.version,
        u.trip_id,
        s.stop_name as destino
    from ultima_parada u
    left join (
        select version, trim(cast(stop_id as varchar)) as stop_id, trim(stop_name) as stop_name
        from {{ source('gtfs', 'stops') }}
    ) s on u.last_stop_id = s.stop_id and u.version = s.version
),

ranked as (
    select
        g.trip_id,
        g.route_id,
        g.route_short_name as linea,
        g.route_long_name,
        g.trip_headsign,
        d.destino,
        row_number() over (partition by g.trip_id order by g.version desc) as rn
    from {{ ref('stg_gtfs') }} g
    left join destinos d
        on g.trip_id = d.trip_id and g.version = d.version
)

select trip_id, route_id, linea, route_long_name, trip_headsign, destino
from ranked
where rn = 1
