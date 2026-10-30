-- Staging de trip_updates: normalización de identificadores (H12'),
-- filtrado de rangos del EDA (-5 a +120 min) y derivación de tiempos locales.
with src as (
    select * from {{ source('bronze', 'trip_updates') }}
)

select
    date                                                    as fecha,
    snapshot_ts,
    to_timestamp(snapshot_ts)                               as snapshot_at_utc,
    timezone('Europe/Madrid', to_timestamp(snapshot_ts))    as snapshot_at_local,
    entity_id,
    trim(trip_id)                                           as trip_id,
    vehicle_id,
    stop_sequence,
    trim(stop_id)                                           as stop_id,
    arrival_delay,
    round(arrival_delay / 60.0, 2)                          as arrival_delay_min,
    arrival_time,
    departure_delay,
    departure_time,
    schedule_relationship
from src
where trip_id is not null
  and arrival_delay is not null
  and arrival_delay between -300 and 7200
