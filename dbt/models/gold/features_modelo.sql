-- Dataset de entrenamiento del modelo predictivo (K6):
-- cada observación intermedia de un viaje es un ejemplo; el objetivo es
-- el retraso final consumado de ese viaje (predicción a N min vista).
with obs as (
    select
        r.fecha,
        r.trip_id,
        r.linea,
        r.snapshot_ts,
        r.arrival_delay_min      as retraso_actual_min,
        r.stop_sequence,
        r.hora_local,
        r.dia_semana,
        l.retraso_final_min,
        l.primer_snapshot_ts,
        l.n_observaciones
    from {{ ref('retrasos_observados') }} r
    join {{ ref('llegadas_consumadas') }} l
        on r.fecha = l.fecha and r.trip_id = l.trip_id
    where r.linea is not null             -- línea por GTFS o por vehicle_label
      and l.n_observaciones >= 5          -- viajes con seguimiento suficiente
)

select
    fecha,
    trip_id,
    linea,
    snapshot_ts,
    retraso_actual_min,
    stop_sequence,
    hora_local,
    dia_semana,
    dia_semana in (0, 6)                                  as es_finde,
    round((snapshot_ts - primer_snapshot_ts) / 60.0, 1)   as min_desde_inicio,
    retraso_final_min                                     as target_retraso_final_min
from obs
