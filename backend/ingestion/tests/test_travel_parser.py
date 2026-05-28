import pytest
from ingestion.parsers.travel import parse_travel_file, normalize_travel_rows, haversine_km
from ingestion.normalizers.flags import (
    MISSING_DESTINATION, MISSING_TRAVEL_CLASS, UNKNOWN_AIRPORT,
)

SAMPLE_TRAVEL = b"""trip_id,traveler_id,traveler_name,trip_type,departure_date,return_date,origin_iata,destination_iata,travel_class,airline,hotel_name,hotel_city,hotel_checkin,hotel_checkout,hotel_nights,ground_transport_type,ground_transport_km,cost_usd,currency
TRP-001,EMP-042,Anna Schmidt,flight,2024-01-15,2024-01-17,BER,LHR,economy,British Airways,,,,,,,, 820.00,EUR
TRP-001,EMP-042,Anna Schmidt,hotel,2024-01-15,2024-01-17,,,,,"The Ritz London",London,2024-01-15,2024-01-17,2,,,,380.00,GBP
TRP-004,EMP-088,Jonas Weber,flight,2024-02-10,,MUC,,economy,Emirates,,,,,,,, 950.00,EUR
"""


def test_haversine_km():
    # BER to LHR approx 933 km
    dist = haversine_km(52.3667, 13.5033, 51.4700, -0.4543)
    assert 900 < dist < 1000


def test_parse_travel_file():
    rows = parse_travel_file(SAMPLE_TRAVEL)
    assert len(rows) == 3


def test_normalize_flight_happy_path():
    rows = parse_travel_file(SAMPLE_TRAVEL)
    results = normalize_travel_rows(rows)
    fields, flags = results[0]
    assert fields["scope"] == 3
    assert fields["travel_subcategory"] == "flight"
    assert fields["distance_km"] is not None
    assert MISSING_DESTINATION not in flags


def test_normalize_hotel_happy_path():
    rows = parse_travel_file(SAMPLE_TRAVEL)
    results = normalize_travel_rows(rows)
    fields, flags = results[1]
    assert fields["travel_subcategory"] == "hotel"
    assert fields["activity_unit_normalized"] == "nights"


def test_normalize_missing_destination():
    rows = parse_travel_file(SAMPLE_TRAVEL)
    results = normalize_travel_rows(rows)
    fields, flags = results[2]
    assert MISSING_DESTINATION in flags
