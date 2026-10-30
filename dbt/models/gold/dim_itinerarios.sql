-- Itinerario completo y ordenado de cada viaje (stop_times, última versión
-- GTFS que conoce el trip). Lo consulta la API para mostrar las estaciones
-- restantes reales de un tren (con filtro por trip_id: predicate pushdown).
with st as (
    select
        version,
        trim(trip_id)                                   as trip_id,
        -- stop_sequence llega como varchar con ceros ('005'): a entero
        cast(trim(cast(stop_sequence as varchar)) as integer) as stop_sequence,
        trim(cast(stop_id as varchar))                  as stop_id,
        trim(cast(arrival_time as varchar))             as hora_prog
    from {{ source('gtfs', 'stop_times') }}
),

ultima_version as (
    select trip_id, max(version) as version
    from st
    group by trip_id
),

filtrado as (
    select st.*
    from st
    join ultima_version u
        on st.trip_id = u.trip_id and st.version = u.version
),

stops as (
    select
        version,
        trim(cast(stop_id as varchar)) as stop_id,
        trim(stop_name)                as stop_name
    from {{ source('gtfs', 'stops') }}
)

select
    f.trip_id,
    f.stop_sequence,
    f.stop_id,
    f.hora_prog,
    s.stop_name
from filtrado f
left join stops s
    on f.stop_id = s.stop_id and f.version = s.version
