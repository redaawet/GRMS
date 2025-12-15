from decimal import Decimal


def fmt_km(x):
    if x is None:
        return "?"
    try:
        return f"{Decimal(str(x)):.3f}"
    except Exception:
        return str(x)


def road_id(road):
    return getattr(road, "road_identifier", None) or f"Road {getattr(road, 'pk', '?')}"


def section_id(section):
    r = getattr(section, "road", None)
    seq = getattr(section, "sequence_on_road", None)
    if r and seq is not None:
        return f"{road_id(r)}-S{seq}"
    return f"Section {getattr(section, 'pk', '?')}"


def segment_id(segment):
    sec = getattr(segment, "section", None)
    s_seq = getattr(segment, "sequence_on_section", None)
    base = section_id(sec) if sec else "Section ?"
    if s_seq is not None:
        return f"{base}-Sg{s_seq}"
    return f"{base}-Sg{getattr(segment, 'pk', '?')}"


def segment_label(segment):
    return (
        f"{segment_id(segment)} "
        f"({fmt_km(getattr(segment,'station_from_km',None))}–{fmt_km(getattr(segment,'station_to_km',None))} km)"
    )


def structure_label(structure):
    r = getattr(structure, "road", None)
    rid = road_id(r) if r else "UNKNOWN"
    cat = getattr(structure, "structure_category", "Structure")
    st = getattr(structure, "station_km", None)
    ch0 = getattr(structure, "start_chainage_km", None)
    ch1 = getattr(structure, "end_chainage_km", None)

    if st is not None:
        return f"{cat} at {fmt_km(st)} km on {rid}"
    if ch0 is not None and ch1 is not None:
        return f"{cat} from {fmt_km(ch0)}–{fmt_km(ch1)} km on {rid}"
    return f"{cat} on {rid}"
