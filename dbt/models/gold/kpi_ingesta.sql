-- K1 (disponibilidad) y K2 (frescura) calculados desde el propio Bronze:
-- snapshots/día, cadencia media y huecos > 2 min, por feed.
with snapshots as (
    select 'trip_updates' as feed, date as fecha, snapshot_ts
    from (select distinct date, snapshot_ts from {{ source('bronze', 'trip_updates') }})
    union all
    select 'vehicle_positions', date, snapshot_ts
    from (select distinct date, snapshot_ts from {{ source('bronze', 'vehicle_positions') }})
    union all
    select 'alerts', date, snapshot_ts
    from (select distinct date, snapshot_ts from {{ source('bronze', 'alerts') }})
),

con_gap as (
    select
        feed,
        fecha,
        snapshot_ts,
        snapshot_ts - lag(snapshot_ts) over (partition by feed, fecha order by snapshot_ts) as gap_s
    from snapshots
)

select
    feed,
    fecha,
    count(*)                                        as n_snapshots,
    round(avg(gap_s), 1)                            as cadencia_media_s,
    max(gap_s)                                      as hueco_max_s,
    count(*) filter (where gap_s > 120)             as n_huecos_2min,
    -- disponibilidad aproximada: % de la ventana operativa (20h) cubierta
    round(least(count(*) / (20 * 3600.0 / 30) * 100, 100), 1) as disponibilidad_pct
from con_gap
group by feed, fecha
order by fecha desc, feed
