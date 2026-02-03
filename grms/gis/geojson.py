from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional


def to_4326(geom):
    if not geom:
        return None
    if isinstance(geom, dict):
        srid = geom.get("srid")
        if srid and srid != 4326:
            return None
        return geom
    srid = getattr(geom, "srid", None)
    if srid and srid != 4326 and hasattr(geom, "transform"):
        try:
            return geom.transform(4326, clone=True)
        except Exception:
            return None
    return geom


def geom_to_geojson(geom_4326) -> Optional[Dict[str, Any]]:
    if not geom_4326:
        return None
    if isinstance(geom_4326, dict):
        return geom_4326 if geom_4326.get("type") else None
    geojson = getattr(geom_4326, "geojson", None)
    if geojson:
        try:
            return json.loads(geojson)
        except Exception:
            return None
    return None


def feature(geom, role: str, feature_id: Optional[int] = None, extra_props: Optional[Dict[str, Any]] = None):
    props = {"role": role}
    if feature_id is not None:
        props["id"] = feature_id
    if extra_props:
        props.update(extra_props)
    return {
        "type": "Feature",
        "geometry": geom_to_geojson(geom),
        "properties": props,
    }


def feature_collection(features: Iterable[Dict[str, Any]]):
    return {"type": "FeatureCollection", "features": list(features)}
