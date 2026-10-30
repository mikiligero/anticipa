-- Dimensión de estaciones (última versión del GTFS estático).
with ranked as (
    select
        trim(cast(stop_id as varchar)) as stop_id,
        trim(stop_name)                as stop_name,
        stop_lat,
        stop_lon,
        row_number() over (partition by trim(cast(stop_id as varchar)) order by version desc) as rn
    from {{ source('gtfs', 'stops') }}
)

select stop_id, stop_name, stop_lat, stop_lon
from ranked
where rn = 1
