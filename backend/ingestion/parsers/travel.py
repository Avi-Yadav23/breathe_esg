import csv
import io
import logging
import math
from decimal import Decimal, InvalidOperation

from . import ParseError
from ..normalizers.flags import (
    UNKNOWN_AIRPORT, MISSING_DESTINATION, MISSING_TRAVEL_CLASS, MISSING_DISTANCE,
    MISSING_QUANTITY,
)

logger = logging.getLogger(__name__)

AIRPORT_COORDS = {
    "BER": (52.3667, 13.5033), "LHR": (51.4700, -0.4543),
    "FRA": (50.0333, 8.5706),  "JFK": (40.6398, -73.7789),
    "MUC": (48.3538, 11.7861), "DXB": (25.2528, 55.3644),
    "CDG": (49.0097, 2.5479),  "AMS": (52.3086, 4.7639),
    "MAD": (40.4719, -3.5626), "SIN": (1.3644, 103.9915),
    "HKG": (22.3080, 113.9185), "SYD": (-33.9399, 151.1753),
    "ORD": (41.9742, -87.9073), "LAX": (33.9425, -118.4081),
    "DEL": (28.5562, 77.1000), "BOM": (19.0896, 72.8656),
    "NRT": (35.7720, 140.3929), "PEK": (40.0799, 116.6031),
    "GRU": (-23.4356, -46.4731), "ICN": (37.4602, 126.4407),
}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Compute great-circle distance between two lat/lon points in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_travel_file(file_content: bytes) -> list[dict]:
    """
    Parse a Navan/Concur-style travel CSV export.
    Returns list of raw row dicts.
    """
    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except UnicodeDecodeError as e:
            raise ParseError(f"Cannot decode file: {e}") from e

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ParseError("File is empty or has no headers")

    rows = [dict(r) for r in reader]
    if not rows:
        raise ParseError("File has headers but no data rows")
    return rows


def normalize_travel_rows(raw_rows: list[dict]) -> list[tuple[dict, list[str]]]:
    """
    Normalize all travel rows. Round-trip detection requires seeing all rows
    for a trip_id together, so we process the full batch.
    """
    # Build trip index: trip_id -> list of (origin, destination) for round-trip detection
    trip_flights: dict[str, list] = {}
    for row in raw_rows:
        trip_id = (row.get("trip_id") or "").strip()
        trip_type = (row.get("trip_type") or "").strip().lower()
        if trip_type == "flight":
            origin = (row.get("origin_iata") or "").strip().upper()
            dest = (row.get("destination_iata") or "").strip().upper()
            trip_flights.setdefault(trip_id, []).append((origin, dest))

    results = []

    for raw_row in raw_rows:
        flags = []
        trip_type = (raw_row.get("trip_type") or "").strip().lower()
        trip_id = (raw_row.get("trip_id") or "").strip()

        fields = {
            "source_type": "travel",
            "scope": 3,
            "category": "business_travel",
            "travel_subcategory": trip_type,
            "activity_value": None,
            "activity_unit": "",
            "activity_unit_normalized": "",
            "activity_value_normalized": None,
            "period_start": None,
            "period_end": None,
            "facility_name": "",
            "plant_code": "",
            "location_country": "",
            "origin_iata": "",
            "destination_iata": "",
            "travel_class": "",
            "distance_km": None,
            "flag_reasons": flags,
        }

        # Departure date
        dep_str = (raw_row.get("departure_date") or "").strip()
        if dep_str:
            from datetime import datetime
            try:
                dep_date = datetime.strptime(dep_str, "%Y-%m-%d").date()
                fields["period_start"] = dep_date
                fields["period_end"] = dep_date
            except ValueError:
                from ..normalizers.flags import BAD_DATE
                flags.append(BAD_DATE)

        if trip_type == "flight":
            origin = (raw_row.get("origin_iata") or "").strip().upper()
            dest = (raw_row.get("destination_iata") or "").strip().upper()
            travel_class = (raw_row.get("travel_class") or "").strip().lower()

            fields["origin_iata"] = origin
            fields["destination_iata"] = dest
            fields["travel_class"] = travel_class

            if not dest:
                flags.append(MISSING_DESTINATION)

            if not travel_class:
                flags.append(MISSING_TRAVEL_CLASS)

            # Compute distance
            if origin and dest:
                if origin not in AIRPORT_COORDS:
                    flags.append(UNKNOWN_AIRPORT)
                elif dest not in AIRPORT_COORDS:
                    flags.append(UNKNOWN_AIRPORT)
                else:
                    lat1, lon1 = AIRPORT_COORDS[origin]
                    lat2, lon2 = AIRPORT_COORDS[dest]
                    dist = Decimal(str(round(haversine_km(lat1, lon1, lat2, lon2), 2)))

                    # Double distance for confirmed round-trip
                    return_date = (raw_row.get("return_date") or "").strip()
                    flights = trip_flights.get(trip_id, [])
                    is_round_trip = (
                        bool(return_date) and
                        any(f[0] == dest and f[1] == origin for f in flights)
                    )
                    if is_round_trip:
                        dist = dist * 2

                    fields["distance_km"] = dist
                    fields["activity_value"] = dist
                    fields["activity_value_normalized"] = dist
                    fields["activity_unit"] = "km"
                    fields["activity_unit_normalized"] = "km"
            else:
                flags.append(MISSING_DISTANCE)

        elif trip_type == "hotel":
            nights_str = (raw_row.get("hotel_nights") or "").strip()
            fields["facility_name"] = (raw_row.get("hotel_name") or "").strip()
            city = (raw_row.get("hotel_city") or "").strip()
            if city:
                fields["facility_name"] = f"{fields['facility_name']} ({city})".strip(" ()")
            if nights_str:
                try:
                    nights = Decimal(nights_str)
                    fields["activity_value"] = nights
                    fields["activity_value_normalized"] = nights
                    fields["activity_unit"] = "nights"
                    fields["activity_unit_normalized"] = "nights"
                except InvalidOperation:
                    flags.append(MISSING_QUANTITY)
            else:
                flags.append(MISSING_QUANTITY)

        elif trip_type == "ground":
            km_str = (raw_row.get("ground_transport_km") or "").strip()
            if km_str:
                try:
                    km = Decimal(km_str)
                    fields["activity_value"] = km
                    fields["activity_value_normalized"] = km
                    fields["activity_unit"] = "km"
                    fields["activity_unit_normalized"] = "km"
                except InvalidOperation:
                    flags.append(MISSING_DISTANCE)
            else:
                flags.append(MISSING_DISTANCE)

        fields["flag_reasons"] = flags
        results.append((fields, flags))

    return results
