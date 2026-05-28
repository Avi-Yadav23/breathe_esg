import pytest
from decimal import Decimal
from ingestion.parsers.utility import parse_utility_file, normalize_utility_rows
from ingestion.normalizers.flags import (
    DUPLICATE_PERIOD, LONG_BILLING_PERIOD, ZERO_CONSUMPTION, OUTLIER_VALUE,
)

SAMPLE_CSV = b"""meter_id,account_number,facility_name,address,billing_period_start,billing_period_end,consumption_kwh,demand_kw,unit,tariff_code,supplier,invoice_number
MTR-001,ACC-8823,Berlin HQ,Addr,2024-01-05,2024-02-04,48320.50,125.4,kWh,C3,Vatt,INV-001
MTR-001,ACC-8823,Berlin HQ,Addr,2024-02-05,2024-03-06,51200.00,131.2,kWh,C3,Vatt,INV-002
MTR-003,ACC-9001,Munich Office,Addr,2024-01-01,2024-01-31,0.00,45.0,kWh,SME,SW,INV-004
"""


def test_parse_utility_file_happy_path():
    rows = parse_utility_file(SAMPLE_CSV)
    assert len(rows) == 3


def test_normalize_utility_rows_happy_path():
    rows = parse_utility_file(SAMPLE_CSV)
    results = normalize_utility_rows(rows, set())
    assert len(results) == 3
    fields, flags = results[0]
    assert fields["scope"] == 2
    assert fields["category"] == "electricity"
    assert flags == []


def test_normalize_utility_zero_consumption():
    rows = parse_utility_file(SAMPLE_CSV)
    results = normalize_utility_rows(rows, set())
    fields, flags = results[2]
    assert ZERO_CONSUMPTION in flags


def test_normalize_utility_duplicate_period():
    rows = parse_utility_file(SAMPLE_CSV)
    # Key is (facility_name, period_start, period_end) since meter_id isn't on NormalizedRecord
    existing = {("Berlin HQ", "2024-01-05", "2024-02-04")}
    results = normalize_utility_rows(rows, existing)
    _, flags0 = results[0]
    assert DUPLICATE_PERIOD in flags0


def test_normalize_utility_long_billing_period():
    csv_content = b"""meter_id,account_number,facility_name,address,billing_period_start,billing_period_end,consumption_kwh,demand_kw,unit,tariff_code,supplier,invoice_number
MTR-X,ACC-X,Facility,Addr,2024-01-01,2024-03-01,50000.00,100.0,kWh,C3,Supplier,INV-X
"""
    rows = parse_utility_file(csv_content)
    results = normalize_utility_rows(rows, set())
    _, flags = results[0]
    assert LONG_BILLING_PERIOD in flags
