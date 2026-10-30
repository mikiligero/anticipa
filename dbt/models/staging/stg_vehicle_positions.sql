-- Staging de vehicle_positions: la línea se deriva del vehicle_label
-- (ej. 'C1-23530-PLATF.(2)' → C1) porque Renfe no rellena route_id en RT.
with src as (
    select * from {{ source('bronze', 'vehicle_positions') }}
)

select
    date                                                    as fecha,
    snapshot_ts,
    timezone('Europe/Madrid', to_timestamp(snapshot_ts))    as snapshot_at_local,
    entity_id,
    trim(trip_id)                                           as trip_id,
    vehicle_id,
    vehicle_label,
    regexp_extract(vehicle_label, '^([A-Z]+[0-9]+[a-z]?)', 1) as linea_label,
    latitude,
    longitude,
    bearing,
    speed_ms,
    trim(stop_id)                                           as stop_id,
    current_stop_sequence,
    current_status
from src
where latitude is not null and longitude is not null
