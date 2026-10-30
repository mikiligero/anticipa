-- Retraso observado por (viaje, snapshot), enriquecido con línea y estación.
-- Es el dato central que la plataforma genera y que no existe en el origen.
with tu as (
    select * from {{ ref('stg_trip_updates') }}
),

rec as (
    select * from {{ ref('reconciliacion_viajes') }}
),

vp as (
    -- fallback de línea desde vehicle_label (histórico sin versión GTFS)
    select * from {{ ref('lineas_observadas') }}
),

stops as (
    select stop_id, stop_name
    from (
        select
            trim(cast(stop_id as varchar)) as stop_id,
            trim(stop_name)                as stop_name,
            row_number() over (partition by trim(cast(stop_id as varchar)) order by version desc) as rn
        from {{ source('gtfs', 'stops') }}
    )
    where rn = 1
)

select
    tu.fecha,
    tu.snapshot_ts,
    tu.snapshot_at_local,
    tu.trip_id,
    coalesce(rec.linea, vp.linea_vp) as linea,
    rec.route_id,
    rec.reconciliado,
    tu.stop_sequence,
    tu.stop_id,
    s.stop_name,
    tu.arrival_delay,
    tu.arrival_delay_min,
    extract(hour from tu.snapshot_at_local)                  as hora_local,
    {{ franja_horaria('extract(hour from tu.snapshot_at_local)') }} as franja,
    dayofweek(tu.snapshot_at_local)                          as dia_semana
from tu
left join rec
    on tu.fecha = rec.fecha and tu.trip_id = rec.trip_id
left join vp
    on tu.fecha = vp.fecha and tu.trip_id = vp.trip_id
left join stops s
    on tu.stop_id = s.stop_id
