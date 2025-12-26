HELP_TEXTS = {
    "grms.Road": {
        "road_identifier": "Unique identifier for the road (e.g., RTR-1).",
        "road_name_from": "Origin settlement or landmark.",
        "road_name_to": "Destination settlement or landmark.",
    },
    "grms.RoadSection": {
        "road": "Select the parent road. Type to search by identifier or name.",
        "start_chainage_km": "Section start chainage in kilometers.",
        "end_chainage_km": "Section end chainage in kilometers (must be greater than start).",
    },
    "grms.RoadSegment": {
        "section": "Select the parent section. Results are filtered by the chosen road.",
        "station_from_km": "Segment start chainage in kilometers.",
        "station_to_km": "Segment end chainage in kilometers (must be greater than start).",
    },
    "grms.StructureInventory": {
        "road": "Select the parent road. Type to search by identifier or name.",
        "section": "Optional parent section; filtered by the selected road.",
        "easting_m": "UTM Easting (meters). Provide together with Northing.",
        "northing_m": "UTM Northing (meters). Provide together with Easting.",
        "derived_lat_lng": "Derived WGS84 latitude/longitude (read-only).",
    },
    "grms.RoadConditionSurvey": {
        "road_segment": "Select the road segment to be surveyed (filtered by road and section).",
        "inspection_date": "Date of field inspection.",
    },
    "grms.StructureConditionSurvey": {
        "structure": "Select a structure on the chosen road/section.",
        "qa_status": "Quality assurance status.",
    },
    "traffic.TrafficSurvey": {
        "road": "Select the road for this traffic survey.",
        "survey_year": "Fiscal year of the survey.",
        "qa_status": "Quality assurance status.",
    },
}
