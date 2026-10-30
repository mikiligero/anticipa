-- Línea de cada viaje derivada del vehicle_label del feed vehicle_positions
-- (ej. 'C1-23530-PLATF.(2)' → C1). Es el fallback de reconciliación para el
-- histórico: los trip_id antiguos referencian versiones semanales del GTFS
-- que no se conservaron, pero el label viaja en el propio feed.
select
    fecha,
    trip_id,
    mode(linea_label) as linea_vp
from {{ ref('stg_vehicle_positions') }}
where linea_label is not null
  and trip_id is not null
group by fecha, trip_id
