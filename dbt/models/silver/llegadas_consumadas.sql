-- Puntualidad "consumada" por viaje y día: última observación de cada
-- viaje (mayor stop_sequence y, a igualdad, snapshot más tardío), que
-- aproxima el retraso en la parada terminal (refinamiento del Sprint 1).
--
-- Implementado con arg_max (agregación hash, spillable) en lugar de
-- funciones de ventana: sobre el histórico completo (~decenas de millones
-- de filas) las ventanas agotaban la memoria del contenedor.
with base as (
    select
        *,
        -- clave de ordenación: stop_sequence manda, snapshot_ts desempata
        (cast(coalesce(stop_sequence, 0) as bigint) * 100000000000 + snapshot_ts) as orden
    from {{ ref('retrasos_observados') }}
),

agregado as (
    select
        fecha,
        trip_id,
        arg_max(linea, orden)              as linea,
        arg_max(route_id, orden)           as route_id,
        arg_max(reconciliado, orden)       as reconciliado,
        arg_max(stop_sequence, orden)      as ultima_stop_sequence,
        arg_max(stop_id, orden)            as ultima_stop_id,
        arg_max(stop_name, orden)          as ultima_stop_name,
        arg_max(arrival_delay_min, orden)  as retraso_final_min,
        arg_max(snapshot_at_local, orden)  as ultima_observacion_local,
        arg_max(hora_local, orden)         as hora_local,
        arg_max(franja, orden)             as franja,
        arg_max(dia_semana, orden)         as dia_semana,
        count(*)                           as n_observaciones,
        min(snapshot_ts)                   as primer_snapshot_ts
    from base
    group by fecha, trip_id
)

select
    *,
    retraso_final_min <= 5 as puntual   -- umbral de puntualidad: 5 min
from agregado
