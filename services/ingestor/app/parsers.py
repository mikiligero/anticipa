"""Parseo de los feeds GTFS-Realtime de Renfe a filas planas.

El Bronze importado y el nuevo mantienen el mismo contrato de campos.
"""
from __future__ import annotations

from datetime import datetime, timezone

from google.transit import gtfs_realtime_pb2


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_feed(feed_name: str, payload: bytes) -> tuple[int, list[dict]]:
    """Devuelve (header_timestamp, filas) para un payload protobuf."""
    msg = gtfs_realtime_pb2.FeedMessage()
    msg.ParseFromString(payload)
    ts = int(msg.header.timestamp)
    if feed_name == "vehicle_positions":
        return ts, _parse_vehicle_positions(msg, ts)
    if feed_name == "trip_updates":
        return ts, _parse_trip_updates(msg, ts)
    if feed_name == "alerts":
        return ts, _parse_alerts(msg, ts)
    raise ValueError(f"Feed desconocido: {feed_name}")


def _parse_vehicle_positions(msg, snapshot_ts: int) -> list[dict]:
    rows = []
    ingested_at = _utcnow()
    for entity in msg.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        rows.append(
            {
                "snapshot_ts": snapshot_ts,
                "ingested_at": ingested_at,
                "entity_id": entity.id,
                "trip_id": v.trip.trip_id or None,
                "vehicle_id": v.vehicle.id or None,
                "vehicle_label": v.vehicle.label or None,
                "latitude": v.position.latitude if v.HasField("position") else None,
                "longitude": v.position.longitude if v.HasField("position") else None,
                "bearing": v.position.bearing if v.HasField("position") else None,
                "speed_ms": v.position.speed if v.HasField("position") else None,
                "stop_id": v.stop_id or None,
                "current_stop_sequence": v.current_stop_sequence,
                "current_status": v.current_status,
                "vehicle_ts": int(v.timestamp) if v.timestamp else None,
            }
        )
    return rows


def _parse_trip_updates(msg, snapshot_ts: int) -> list[dict]:
    rows = []
    ingested_at = _utcnow()
    for entity in msg.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        base = {
            "snapshot_ts": snapshot_ts,
            "ingested_at": ingested_at,
            "entity_id": entity.id,
            "trip_id": tu.trip.trip_id or None,
            "vehicle_id": tu.vehicle.id or None,
        }
        # Renfe publica una única stop_time_update por entidad (próxima parada)
        for stu in tu.stop_time_update:
            rows.append(
                {
                    **base,
                    "stop_sequence": stu.stop_sequence,
                    "stop_id": stu.stop_id or None,
                    "arrival_delay": stu.arrival.delay if stu.HasField("arrival") else None,
                    "arrival_time": int(stu.arrival.time) if stu.HasField("arrival") and stu.arrival.time else None,
                    "departure_delay": stu.departure.delay if stu.HasField("departure") else None,
                    "departure_time": int(stu.departure.time) if stu.HasField("departure") and stu.departure.time else None,
                    "schedule_relationship": stu.schedule_relationship,
                }
            )
    return rows


def _parse_alerts(msg, snapshot_ts: int) -> list[dict]:
    rows = []
    ingested_at = _utcnow()
    for entity in msg.entity:
        if not entity.HasField("alert"):
            continue
        a = entity.alert
        start, end = None, None
        if a.active_period:
            start = int(a.active_period[0].start) or None
            end = int(a.active_period[0].end) or None  # end=0 → None (sin fin)
        routes = ",".join(sorted({ie.route_id for ie in a.informed_entity if ie.route_id}))
        stops = ",".join(sorted({ie.stop_id for ie in a.informed_entity if ie.stop_id}))
        rows.append(
            {
                "snapshot_ts": snapshot_ts,
                "ingested_at": ingested_at,
                "entity_id": entity.id,
                "cause": a.cause,
                "effect": a.effect,
                "active_start": start,
                "active_end": end,
                "informed_routes": routes or None,
                "informed_stops": stops or None,
                "header_text": _first_translation(a.header_text),
                "description_text": _first_translation(a.description_text),
            }
        )
    return rows


def _first_translation(ts) -> str | None:
    for t in ts.translation:
        if t.text:
            return t.text
    return None
