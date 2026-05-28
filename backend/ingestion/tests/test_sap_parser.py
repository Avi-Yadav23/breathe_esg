import pytest
from decimal import Decimal
from ingestion.parsers.sap import parse_sap_file, normalize_sap_row, MATERIAL_FUEL_MAP
from ingestion.parsers import ParseError
from ingestion.normalizers.flags import (
    MISSING_QUANTITY, BAD_DATE, UNKNOWN_MATERIAL, UNKNOWN_PLANT,
)


SAMPLE_SAP_CONTENT = b"""Buchungskreis\tWerk\tBelegdatum\tBuchdatum\tMaterial\tMaterialbez\tBewArt\tMenge\tMengenEinh\tBetrag\tW\xe4hrung\tKostenstelle
1000\t1001\t15.01.2024\t15.01.2024\tFUEL-DI\tDieselkraftstoff\t101\t5000.000\tL\t8500.00\tEUR\t4100
1000\t1001\t14.02.2024\t14.02.2024\tFUEL-DI\tDieselkraftstoff\t101\t\tL\t4200.00\tEUR\t4100
"""


def test_parse_sap_file_happy_path():
    rows = parse_sap_file(SAMPLE_SAP_CONTENT)
    assert len(rows) == 2
    assert rows[0]["Werk"] == "1001"
    assert rows[0]["Material"] == "FUEL-DI"


def test_normalize_sap_row_happy_path():
    raw = {
        "Buchungskreis": "1000", "Werk": "1001", "Belegdatum": "15.01.2024",
        "Buchdatum": "15.01.2024", "Material": "FUEL-DI", "Materialbez": "Dieselkraftstoff",
        "BewArt": "101", "Menge": "5000.000", "MengenEinh": "L",
        "Betrag": "8500.00", "Währung": "EUR", "Kostenstelle": "4100",
    }
    fields, flags = normalize_sap_row(raw)
    assert flags == []
    assert fields["scope"] == 1
    assert fields["category"] == "diesel"
    assert fields["activity_value"] == Decimal("5000.000")
    assert fields["activity_unit_normalized"] == "liters"
    assert fields["location_country"] == "DE"


def test_normalize_sap_row_missing_quantity():
    raw = {
        "Buchungskreis": "1000", "Werk": "1001", "Belegdatum": "15.01.2024",
        "Buchdatum": "15.01.2024", "Material": "FUEL-DI", "Materialbez": "Diesel",
        "BewArt": "101", "Menge": "", "MengenEinh": "L",
        "Betrag": "4200.00", "Währung": "EUR", "Kostenstelle": "4100",
    }
    fields, flags = normalize_sap_row(raw)
    assert MISSING_QUANTITY in flags


def test_normalize_sap_row_bad_date():
    raw = {
        "Buchungskreis": "1000", "Werk": "1001", "Belegdatum": "not-a-date",
        "Buchdatum": "15.01.2024", "Material": "FUEL-DI", "Materialbez": "Diesel",
        "BewArt": "101", "Menge": "1000", "MengenEinh": "L",
        "Betrag": "2000.00", "Währung": "EUR", "Kostenstelle": "4100",
    }
    fields, flags = normalize_sap_row(raw)
    assert BAD_DATE in flags


def test_normalize_sap_row_unknown_material():
    raw = {
        "Buchungskreis": "1000", "Werk": "1001", "Belegdatum": "15.01.2024",
        "Buchdatum": "15.01.2024", "Material": "FUEL-UNKNOWN", "Materialbez": "Unknown",
        "BewArt": "101", "Menge": "500", "MengenEinh": "L",
        "Betrag": "1000.00", "Währung": "EUR", "Kostenstelle": "4100",
    }
    fields, flags = normalize_sap_row(raw)
    assert UNKNOWN_MATERIAL in flags
